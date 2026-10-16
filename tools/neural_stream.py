"""Bounded sentence-batched speech production, not incremental Kokoro inference.

One producer, at most two published/unacknowledged chunks, twelve chunks and 60s
PCM total. Slow/disconnected clients expire instead of retaining a worker forever.
"""
import copy
import json
import re
import shutil
import textwrap
import time
import uuid
import wave

from neural_session import text_hash, validate_binding
from analyze_neural_clips import audio_metadata, validate_timeline
from local_neural_speech import validate_request
from neural_cancel import GenerationCancelled

MAX_PENDING=2
MAX_CHUNKS=12
MAX_STREAM_CHARACTERS=1000
CONSUMER_TIMEOUT=75


def sentence_batches(text):
    if not isinstance(text,str) or len(text)>MAX_STREAM_CHARACTERS:raise ValueError('Sentence mode accepts up to 1000 characters; use shorter paragraphs (60 seconds maximum)')
    # Apply the same Unicode/control validation without relaxing single-call TTS.
    for start in range(0,len(text),499):validate_request('x'+text[start:start+499])
    if not text.strip():raise ValueError('Enter nonblank text')
    pieces=[]
    for sentence in re.split(r'(?<=[.!?])\s+',text.strip()):
        for part in textwrap.wrap(sentence,width=160,break_long_words=False,break_on_hyphens=False):
            if len(part)>160:raise ValueError('Sentence batching needs words shorter than 160 characters')
            pieces.append(part)
    if not 1<=len(pieces)<=MAX_CHUNKS:raise ValueError('Use at most twelve sentence batches or choose whole-utterance mode')
    return pieces


def merge_sessions(ident,text,root,clips,rig):
    directory=root/ident;directory.mkdir(exist_ok=False)
    rate=None;samples=0;cues=[];sources=[]
    with wave.open(str(directory/'audio.wav'),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2)
        for clip in clips:
            wav=root/clip['id']/'audio.wav'
            binding=json.loads((root/clip['id']/'cues.json').read_text(encoding='utf-8'))
            validate_binding(clip,wav,binding,rig)
            with wave.open(str(wav),'rb') as source:
                if rate is None:rate=source.getframerate();output.setframerate(rate)
                if source.getframerate()!=rate:raise ValueError('Batch sample rates differ; no implicit resampling')
                count=source.getnframes()
                if samples+count>rate*60:raise ValueError('Batch exceeds 60 seconds')
                output.writeframes(source.readframes(count))
            for cue in clip['cues']:cues.append({'start':samples/rate+cue['start'],'end':samples/rate+cue['end'],'value':cue['value']})
            # Cue ends can be rounded by the analyzer. Normalize only the final
            # boundary to the actual source sample count before concatenation.
            cues[-1]['end']=(samples+count)/rate
            sources.append({'id':clip['id'],'audio_sha256':clip['audio']['sha256'],'text_sha256':clip['text_sha256'],'start_sample':samples,'samples':count,'analysis':clip['analysis']})
            samples+=count
    metrics=audio_metadata(directory/'audio.wav')
    analysis={'method':'Per-sentence exact-WAV/dialog Rhubarb estimates, shifted by integer PCM offsets; no whole-WAV reanalysis',
        'audio_sha256':metrics['sha256'],'sources':sources,'hand_verified':False,'phoneme_forced_alignment':False,'espeak_timings_reused':False}
    binding={'metadata':{'duration':samples/rate,'soundFile':'audio.wav'},'mouthCues':cues,'provenance':analysis}
    validate_timeline(binding,samples/rate)
    clip=copy.deepcopy(clips[0]);clip.update(id=ident,title='Sentence-batched performance',text=text,text_sha256=text_hash(text),file=f'/sessions/{ident}/audio.wav',
        audio=metrics,duration=samples/rate,cues=cues,analysis=analysis,
        generation_seconds=sum(c['generation_seconds'] for c in clips),analysis_seconds=sum(c['analysis_seconds'] for c in clips),
        total_seconds=sum(c['total_seconds'] for c in clips),stream={'mode':'sentence-batched','chunks':len(clips),'sample_rate':rate,'samples':samples,'max_pending':MAX_PENDING},
        limits='Sentence-batched whole-chunk inference/analysis, not native incremental TTS. Boundaries/prosody and physical AV quality require review.')
    clip['tts']['engine_load_seconds']=sum(c['tts']['engine_load_seconds'] for c in clips)
    peaks=[c['tts'].get('process_peak_rss_mib') for c in clips]
    clip['tts']['process_peak_rss_mib']=max((p for p in peaks if p is not None),default=None)
    validate_binding(clip,directory/'audio.wav',binding,rig)
    for name,value in [('cues.json',binding),('manifest.json',clip)]:
        (directory/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    (directory/'requested-text.txt').write_text(text,encoding='utf-8');return clip


def perform_stream(state,ident,text,batches):
    token=state.tokens[ident];children=[];clips=[];samples=0;rate=None;started=time.monotonic()
    def stage(value):
        with state.condition:
            token.check();state.jobs[ident]['stage']=value
    stage.cancel_token=token
    stage.speaker=state.speakers.get(ident,dict(id="default",name="Default",voice="af_heart",speed=1.0))
    def wait_capacity(finish=False):
        deadline=time.monotonic()+CONSUMER_TIMEOUT
        with state.condition:
            while len(state.streams[ident]['pending']) >= (1 if finish else MAX_PENDING):
                token.check()
                if time.monotonic()>deadline:raise TimeoutError('Sentence consumer stopped acknowledging chunks')
                state.condition.wait(.1)
            token.check()
    try:
        for index,text_part in enumerate(batches):
            wait_capacity();child=uuid.uuid4().hex;children.append(child)
            clip=state.pipeline(child,text_part,state.root/child,state.rig,state.rhubarb,stage);token.check()
            with wave.open(str(state.root/child/'audio.wav'),'rb') as wav:
                if rate is None:rate=wav.getframerate()
                if wav.getframerate()!=rate:raise ValueError('Inconsistent batch sample rate')
                count=wav.getnframes()
            if samples+count>rate*60:raise ValueError('60-second stream budget exceeded')
            item={'index':index,'id':child,'start_sample':samples,'end_sample':samples+count,'clip':clip};samples+=count;clips.append(clip)
            with state.condition:
                token.check();state.jobs[child]={'state':'ready','stage':'ready','id':child,'clip':clip}
                stream=state.streams[ident];stream['pending'].append(item);stream['produced']=index+1
                state.jobs[ident].update(chunks=list(stream['pending']),produced=index+1,sample_rate=rate,stage='buffered')
        wait_capacity(finish=True)
        token.check();merged=merge_sessions(ident,text,state.root,clips,state.rig)
        merged['total_seconds']=round(time.monotonic()-started,4)
        (state.root/ident/'manifest.json').write_text(json.dumps(merged,indent=2)+'\n',encoding='utf-8')
        for child in children:shutil.rmtree(state.root/child,ignore_errors=True)
        with state.condition:
            token.check()
            for child in children:state.jobs.pop(child,None)
            state.streams.pop(ident,None);state.tokens.pop(ident,None);state.busy=False
            state.jobs[ident]={'id':ident,'state':'ready','stage':'ready','clip':merged,'mode':'sentence-batched'}
            state.ready.append(ident)
            while len(state.ready)>6:
                old=state.ready.pop(0);state.jobs.pop(old,None);shutil.rmtree(state.root/old,ignore_errors=True)
    except Exception as error:
        shutil.rmtree(state.root/ident,ignore_errors=True)
        for child in children:shutil.rmtree(state.root/child,ignore_errors=True)
        with state.condition:
            for child in children:state.jobs.pop(child,None)
            state.streams.pop(ident,None);state.tokens.pop(ident,None);state.busy=False
            cancelled=isinstance(error,GenerationCancelled) or token.event.is_set()
            state.jobs[ident]={'id':ident,'state':'cancelled' if cancelled else 'error','stage':'cancelled' if cancelled else 'error',
                'error':None if cancelled else f'Sentence batching failed ({type(error).__name__}); partial chunks were discarded.'}
            state.failed.append(ident)
            while len(state.failed)>6:state.jobs.pop(state.failed.pop(0),None)
    finally:
        state.speakers.pop(ident,None)
        for child in children:
            shutil.rmtree(state.root/child,ignore_errors=True)
        with state.condition:
            for child in children:state.jobs.pop(child,None)
            state.streams.pop(ident,None)
            if state.tokens.pop(ident,None) is not None:state.busy=False
            state.condition.notify_all()
