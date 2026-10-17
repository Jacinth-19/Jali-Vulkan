"""Bounded cast, private conversation storage and opt-in local control broker."""
import copy
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
import uuid
from neural_session import MEDIA, SESSION_ID, validate_binding
from studio_voices import VOICES, available
ID=re.compile(r'[a-z][a-z0-9_-]{0,23}\Z')
MAX_TURNS=128
MAX_TEXT=20000
MAX_SAVED=5
MAX_BYTES=50*1024*1024

def speaker(value,voices):
    if not isinstance(value,dict) or not {'id','name','voice','speed'}<=set(value) or set(value)-{'id','name','voice','speed','settings'} or not isinstance(value['id'],str) or not ID.fullmatch(value['id']) or not isinstance(value['name'],str) or not 1<=len(value['name'])<=48 or not value['name'].strip() or any(ord(c)<32 or ord(c)==127 for c in value['name']) or value['voice'] not in voices or type(value['speed']) not in (int,float) or not math.isfinite(value['speed']) or not .75<=value['speed']<=1.25:raise ValueError('Invalid speaker or uninstalled voice')
    if 'settings' in value:
        from neural_visemes import articulation
        from creative_performance import settings,EXPRESSIONS
        p=value['settings']
        if not isinstance(p,dict) or set(p)!={'calibration','creative','mood','gaze','life','appearance'} or p['mood'] not in EXPRESSIONS or p['gaze'] not in ('forward','left','right','down') or type(p['life']) is not bool:raise ValueError('Invalid speaker settings')
        articulation(p['calibration']);settings(p['creative'])
        a=p['appearance']
        if a is not None:
            if not isinstance(a,dict) or set(a) not in ({'lighting','background','camera','exposure','skin','eyes','fxaa'},{'lighting','background','camera','exposure','skin','eyes','fxaa','scattering'}) or a['lighting'] not in ('studio','soft','dramatic') or a['background'] not in ('slate','charcoal','cream','blue','green') or a['camera'] not in ('portrait','close','threequarter','wide') or type(a['fxaa']) is not bool:raise ValueError('Invalid speaker appearance')
            for k,lo,hi in [('exposure',.5,1.8),('skin',.3,1),('eyes',.03,.6),*([('scattering',0,.25)] if 'scattering' in a else [])]:
                if type(a[k]) not in (float,int) or not math.isfinite(a[k]) or not lo<=a[k]<=hi:raise ValueError('Invalid speaker material')
    return copy.deepcopy(value)

def cast(value,voices):
    if not isinstance(value,list) or not 1<=len(value)<=8:raise ValueError('Use 1–8 cast profiles')
    result=[speaker(v,voices) for v in value]
    if len({v['id'] for v in result})!=len(result):raise ValueError('Duplicate speaker identity')
    return result

def conversation(value,voices):
    if not isinstance(value,dict) or set(value)!={'schema','id','name','cast','turns'} or value['schema']!='jali-conversation-v1' or not isinstance(value['id'],str) or not SESSION_ID.fullmatch(value['id']) or not isinstance(value['name'],str) or not 1<=len(value['name'])<=80 or not value['name'].strip() or any(ord(c)<32 or ord(c)==127 for c in value['name']):raise ValueError('Invalid conversation header')
    out=copy.deepcopy(value);out['cast']=cast(value['cast'],voices);ids={s['id'] for s in out['cast']};seen=set();total=0
    if not isinstance(value['turns'],list) or not 1<=len(value['turns'])<=MAX_TURNS:raise ValueError('Use 1–128 turns')
    from local_neural_speech import validate_request
    for turn in value['turns']:
        if not isinstance(turn,dict) or set(turn)!={'id','speaker','text','session'} or not isinstance(turn['id'],str) or not SESSION_ID.fullmatch(turn['id']) or turn['id'] in seen or not isinstance(turn['speaker'],str) or turn['speaker'] not in ids or not isinstance(turn['session'],(str,type(None))) or turn['session'] is not None and not SESSION_ID.fullmatch(turn['session']):raise ValueError('Invalid turn identity/speaker/session')
        validate_request(turn['text'])
        if len(turn['text'])>160:raise ValueError('Turn exceeds 160 characters')
        seen.add(turn['id']);total+=len(turn['text'])
    if total>MAX_TEXT:raise ValueError('Conversation exceeds 20000 characters')
    return out

class ConversationStore:
    """User data survives ephemeral six-session eviction; no arbitrary paths/URLs."""
    def __init__(self,root,voices):self.root=Path(root);self.voices=voices;self.lock=threading.Lock()
    def folder(self,ident):
        if not isinstance(ident,str) or not SESSION_ID.fullmatch(ident):raise ValueError('Invalid conversation identity')
        return self.root/ident
    def list(self):
        if not self.root.exists():return []
        result=[]
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir() or not SESSION_ID.fullmatch(folder.name):continue
            try:name=json.loads((folder/'conversation.json').read_text(encoding='utf-8'))['name']
            except (ValueError,OSError,KeyError):name='Damaged conversation (delete to free slot)'
            result.append({'id':folder.name,'name':name})
        return result
    def load(self,ident):
        data=conversation(json.loads((self.folder(ident)/'conversation.json').read_text(encoding='utf-8')),self.voices)
        return data
    def save(self,value,state):
        value=conversation(value,self.voices)
        with self.lock:
            folder=self.folder(value['id']);self.root.mkdir(parents=True,exist_ok=True)
            if not folder.exists() and len(list(self.root.iterdir()))>=MAX_SAVED:raise ValueError('Five saved conversations maximum; delete one first')
            folder.mkdir(exist_ok=True)
            expected={s['id']:s for s in value['cast']}
            for turn in value['turns']:
                target=folder/turn['id']
                if target.exists():
                    old=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
                    if old['rig']!=state.rig or old['text']!=turn['text'] or old.get('speaker')!=expected[turn['speaker']]:raise ValueError('Saved turn changed; use a new turn ID')
                    continue
                if turn['session'] is None:continue
                job=state.get(turn['session'])
                if not job or job['state']!='ready':continue
                clip=job['clip']
                if clip['text']!=turn['text'] or clip.get('speaker')!=expected[turn['speaker']]:raise ValueError('Saved turn/session speaker or text mismatch')
                source=state.root/turn['session'];validate_binding(clip,source/'audio.wav',json.loads((source/'cues.json').read_text(encoding='utf-8')),state.rig)
                used=sum(p.stat().st_size for p in folder.rglob('*') if p.is_file());size=sum((source/n).stat().st_size for n in MEDIA)
                if used+size>MAX_BYTES:raise ValueError('Saved conversation exceeds 50 MiB')
                temporary=folder/(turn['id']+'.part')
                try:
                    temporary.mkdir()
                    for name in MEDIA:shutil.copy2(source/name,temporary/name)
                    temporary.rename(target)
                finally:shutil.rmtree(temporary,ignore_errors=True)
            body=json.dumps(value,ensure_ascii=False)
            used=sum(p.stat().st_size for p in folder.rglob('*') if p.is_file() and p.name not in ('conversation.json','conversation.part'))
            if used+len(body.encode())>MAX_BYTES:raise ValueError('Saved conversation exceeds 50 MiB')
            temporary=folder/'conversation.part';temporary.write_text(body,encoding='utf-8');temporary.replace(folder/'conversation.json')
            return value
    def delete(self,ident):
        with self.lock:shutil.rmtree(self.folder(ident))
    def replay(self,ident,turn,state):
        data=self.load(ident);item=next((t for t in data['turns'] if t['id']==turn),None)
        if item is None:raise ValueError('Unknown saved turn')
        source=self.folder(ident)/item['id'];clip=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        expected=next(s for s in data['cast'] if s['id']==item['speaker'])
        if clip['text']!=item['text'] or clip.get('speaker')!=expected:raise ValueError('Saved turn text/speaker binding mismatch')
        validate_binding(clip,source/'audio.wav',json.loads((source/'cues.json').read_text(encoding='utf-8')),state.rig)
        with state.lock:
            if state.busy:raise ValueError('Generation is busy')
            new=uuid.uuid4().hex;target=state.root/new;target.mkdir()
            try:
                for name in MEDIA-{'manifest.json'}:shutil.copy2(source/name,target/name)
                clip['id']=new;clip['file']=f'/sessions/{new}/audio.wav';clip['saved_conversation']=ident
                (target/'manifest.json').write_text(json.dumps(clip),encoding='utf-8')
                state.jobs[new]={'id':new,'state':'ready','stage':'ready','clip':clip};state.ready.append(new)
                while len(state.ready)>6:
                    old=state.ready.pop(0);state.jobs.pop(old,None);shutil.rmtree(state.root/old,ignore_errors=True)
                return new
            except Exception:shutil.rmtree(target,ignore_errors=True);raise

class ControlBroker:
    """At-most-once commands. One renewable browser lease; bounded event journal."""
    def __init__(self,key):self.key=key;self.lock=threading.Lock();self.commands=deque();self.events=deque(maxlen=256);self.seq=0;self.owner=None;self.until=0
    def emit(self,kind,data):
        self.seq+=1;self.events.append({'seq':self.seq,'type':kind,'data':copy.deepcopy(data)})
    def submit(self,value):
        if not isinstance(value,dict) or 'type' not in value:raise ValueError('Expected command object')
        kind=value['type'];keys={'submit':{'type','text','speaker'},'pause':{'type'},'resume':{'type'},'interrupt':{'type'},'expression':{'type','expression','intensity'}}
        if kind not in keys or set(value)!=keys[kind]:raise ValueError('Unknown command or fields')
        if kind=='submit':
            from local_neural_speech import validate_request
            validate_request(value['text'])
            if len(value['text'])>160 or not isinstance(value['speaker'],str) or not ID.fullmatch(value['speaker']):raise ValueError('Submit a <=160 character turn and cast ID')
        if kind=='expression':
            from creative_performance import EXPRESSIONS,finite
            if value['expression'] not in EXPRESSIONS or not finite(value['intensity'],0,1):raise ValueError('Invalid manual expression')
        with self.lock:
            if len(self.commands)>=32:raise ValueError('Control queue full')
            ident=uuid.uuid4().hex;self.commands.append({'id':ident,'command':copy.deepcopy(value),'expires':time.monotonic()+60});self.emit('accepted',{'command':ident});return ident
    def poll(self,consumer):
        if not isinstance(consumer,str) or not SESSION_ID.fullmatch(consumer):raise ValueError('Invalid consumer')
        with self.lock:
            now=time.monotonic()
            if self.owner not in (None,consumer) and self.until>now:raise ValueError('Another browser owns playback')
            self.owner=consumer;self.until=now+10
            while self.commands:
                command=self.commands.popleft()
                if command.pop('expires')<now:self.emit('expired',{'command':command['id']});continue
                self.emit('delivered',{'command':command['id']});return command
            return None
    def event(self,consumer,kind,data):
        if kind not in ('play','pause','ended','error','loaded','command-done','command-error','turn-start','turn-done','interrupted','cast'):raise ValueError('Invalid event type')
        if not isinstance(data,dict) or len(json.dumps(data))>4096:raise ValueError('Event exceeds budget')
        with self.lock:
            if consumer!=self.owner or time.monotonic()>self.until:raise ValueError('Playback lease expired')
            self.emit(kind,data)
    def read(self,after):
        if type(after) is not int or not 0<=after<=self.seq:raise ValueError('Invalid event cursor')
        with self.lock:return {'cursor':self.seq,'gap':bool(self.events and after<self.events[0]['seq']-1),'events':[copy.deepcopy(e) for e in self.events if e['seq']>after]}
