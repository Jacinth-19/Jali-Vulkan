import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import wave
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from studio_workspace import cast,conversation,ControlBroker,MAX_BYTES
from neural_studio_server import StudioState,make_server
from upgrade_fixture_server import fixture_pipeline

SP=dict(id='default',name='Default',voice='af_heart',speed=1.0)
def conv(turns):return dict(schema='jali-conversation-v1',id='a'*32,name='Public synthetic transport fixture',cast=[SP],turns=turns)
class WorkspaceTests(unittest.TestCase):
 def test_cast_and_conversation_bounds(self):
  self.assertEqual(cast([SP],['af_heart']),[SP])
  for value in [[SP,SP],[],[{**SP,'speed':float('nan')}],[{**SP,'voice':'not-installed'}],[{**SP,'path':'/secret'}]]:
   with self.assertRaises(ValueError):cast(value,['af_heart'])
  t=dict(id='b'*32,speaker='default',text='Hello.',session=None)
  self.assertEqual(conversation(conv([t]),['af_heart'])['turns'],[t])
  for turns in [[t,t],[{**t,'text':'x'*161}],[{**t,'speaker':'missing'}],[{**t,'session':'../audio.wav'}]]:
   with self.assertRaises(ValueError):conversation(conv(turns),['af_heart'])
 def test_broker_bounds_lease_expiry_and_journal_gap(self):
  broker=ControlBroker('key');first=broker.submit({'type':'submit','text':'Hello.','speaker':'default'});a='a'*32;b='b'*32
  self.assertEqual(broker.poll(a)['id'],first)
  with self.assertRaises(ValueError):broker.poll(b)
  broker.event(a,'play',{'time':0})
  self.assertEqual(broker.read(0)['events'][-1]['type'],'play')
  broker.until=0;self.assertIsNone(broker.poll(b))
  for _ in range(32):broker.submit({'type':'pause'})
  with self.assertRaises(ValueError):broker.submit({'type':'pause'})
  broker.commands[0]['expires']=0;broker.poll(b)
  self.assertTrue(any(e['type']=='expired' for e in broker.events))
  for _ in range(260):broker.event(b,'pause',{})
  self.assertTrue(broker.read(0)['gap']);self.assertEqual(len(broker.events),256)
  for value in [{'type':'expression','expression':'inferred','intensity':1},{'type':'expression','expression':'warm','intensity':float('inf')},{'type':'submit','text':'x'*161,'speaker':'default'},{'type':'pause','shell':'not allowed'}]:
   with self.assertRaises(ValueError):broker.submit(value)
 def test_saved_audio_survives_six_session_eviction_and_hash_tampering_fails(self):
  with tempfile.TemporaryDirectory() as directory:
   state=StudioState(Path(directory)/'sessions',{'test':'fixture'},None,pipeline=fixture_pipeline);turns=[]
   try:
    for i in range(8):
     text=f'Fixture {i}.';ident=state.start(text);deadline=time.monotonic()+5
     while state.get(ident)['state']=='running':
      if time.monotonic()>deadline:self.fail('Fixture timed out')
      time.sleep(.01)
     self.assertEqual(state.get(ident)['state'],'ready');turns.append(dict(id=f'{i+1:032x}',speaker='default',text=text,session=ident));state.conversations.save(conv(turns),state)
    self.assertIsNone(state.get(turns[0]['session']));restored=state.conversations.replay('a'*32,turns[0]['id'],state)
    self.assertEqual(state.get(restored)['clip']['text'],turns[0]['text'])
    source=state.conversations.folder('a'*32)/turns[0]['id']/'audio.wav';source.write_bytes(b'tampered')
    with self.assertRaises((ValueError,EOFError,wave.Error)) as caught:state.conversations.replay('a'*32,turns[0]['id'],state)
    self.assertIsNotNone(caught.exception)
    with self.assertRaises(ValueError):state.conversations.load('../escape')
    changed=copy.deepcopy(turns);changed[0]['text']='Changed text.'
    with self.assertRaises(ValueError):state.conversations.save(conv(changed),state)
   finally:state.cancel_active();state.pool.shutdown(wait=True)
 def test_speaker_snapshot_and_single_worker(self):
  with tempfile.TemporaryDirectory() as directory:
   entered=threading.Event();release=threading.Event()
   def delayed(*args):entered.set();release.wait(3);return fixture_pipeline(*args)
   state=StudioState(Path(directory)/'sessions',{},None,pipeline=delayed)
   try:
    chosen=copy.deepcopy(SP);ident=state.start('Snapshot.',speaker_id=chosen);self.assertTrue(entered.wait(2));chosen['speed']=1.25;state.cast[0]['name']='Changed';self.assertIsNone(state.start('Second job.'));release.set()
    deadline=time.monotonic()+3
    while state.get(ident)['state']=='running':
     if time.monotonic()>deadline:self.fail('Snapshot fixture timed out')
     time.sleep(.01)
    self.assertEqual(state.get(ident)['clip']['speaker'],SP)
   finally:release.set();state.pool.shutdown(wait=True)
 def test_saved_conversation_quota_fails_closed(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as directory:
   state=StudioState(Path(directory)/'sessions',{},None,pipeline=fixture_pipeline)
   try:
    ident=state.start('Quota fixture.');deadline=time.monotonic()+3
    while state.get(ident)['state']=='running':
     if time.monotonic()>deadline:self.fail('Quota fixture timed out')
     time.sleep(.01)
    value=conv([dict(id='b'*32,speaker='default',text='Quota fixture.',session=ident)])
    with patch('studio_workspace.MAX_BYTES',10000):
     with self.assertRaisesRegex(ValueError,'50 MiB'):state.conversations.save(value,state)
    self.assertFalse((state.conversations.folder(value['id'])/'conversation.json').exists());state.conversations.delete(value['id'])
   finally:state.pool.shutdown(wait=True)
 def test_loopback_control_and_ui_tokens_are_separate(self):
  with tempfile.TemporaryDirectory() as directory:
   state=StudioState(Path(directory)/'sessions',{},None,pipeline=fixture_pipeline);state.control=ControlBroker('private-key');server=make_server(directory,state,'127.0.0.1',0);thread=threading.Thread(target=server.serve_forever);thread.start();base=f'http://127.0.0.1:{server.server_port}'
   def call(route,data=None,headers=None):
    req=Request(base+route,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json',**(headers or {})})
    with urlopen(req,timeout=3) as r:return json.load(r)
   try:
    self.assertEqual(call('/api/integration/cast',headers={'Authorization':'Bearer private-key'})['limits']['inference_jobs'],1)
    config=call('/api/config');self.assertNotIn('private-key',json.dumps(config));self.assertTrue(config['integration'])
    for h in [{},{'X-Jali-Token':state.token},{'Authorization':'Bearer private-key','Origin':base}]:
     with self.assertRaises(HTTPError) as e:call('/api/integration/commands',{'type':'pause'},h)
     self.assertEqual(e.exception.code,403)
    ident=call('/api/integration/commands',{'type':'pause'},{'Authorization':'Bearer private-key'})['id'];consumer='b'*32
    command=call('/api/control/poll',{'consumer':consumer},{'X-Jali-Token':state.token});self.assertEqual(command['command']['id'],ident)
    with self.assertRaises(HTTPError):call('/api/conversations')
    self.assertEqual(call('/api/conversations',headers={'X-Jali-Token':state.token})['conversations'],[])
    events=call('/api/integration/events?after=0',headers={'Authorization':'Bearer private-key'});self.assertEqual(events['events'][-1]['type'],'delivered')
   finally:server.shutdown();server.server_close();thread.join();state.pool.shutdown(wait=True)
if __name__=='__main__':unittest.main()
