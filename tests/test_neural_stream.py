"""Explicit model-free stream fixtures, real PCM and queue/cleanup invariants."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_stream import sentence_batches,merge_sessions
from neural_studio_server import StudioState
from neural_session import text_hash
from analyze_neural_clips import audio_metadata


def fake_pipeline(ident,text,directory,rig,rhubarb,stage):
    stage('synthesizing');directory.mkdir()
    with wave.open(str(directory/'audio.wav'),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(struct.pack('<h',1000)*2400)
    audio=audio_metadata(directory/'audio.wav');analysis={'audio_sha256':audio['sha256'],'method':'explicit fake test fixture'}
    cues=[{'start':0,'end':.1,'value':'X'}]
    clip={'id':ident,'text':text,'text_sha256':text_hash(text),'file':f'/sessions/{ident}/audio.wav','duration':.1,'audio':audio,'cues':cues,'rig':rig,'analysis':analysis,'tts':{'engine_load_seconds':.01,'process_peak_rss_mib':1},'generation_seconds':.01,'analysis_seconds':.01,'total_seconds':.02}
    (directory/'cues.json').write_text(json.dumps({'metadata':{'duration':.1},'mouthCues':cues,'provenance':analysis}));return clip


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.calls=[]
        def pipeline(*args):self.calls.append(args[1]);return fake_pipeline(*args)
        self.state=StudioState(self.root,{'test':True},None,pipeline=pipeline)
    def tearDown(self):self.state.cancel_active();self.state.pool.shutdown(wait=True);self.tmp.cleanup()
    def wait(self,predicate):
        until=time.monotonic()+5
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.01)
        self.fail('Stream condition timed out')
    def test_split_preserves_words_and_bounds(self):
        self.assertEqual(sentence_batches('One. Two! Three?'),['One.','Two!','Three?'])
        for text in ['x'*161,'Hi. '*10]:
            with self.assertRaises(ValueError):sentence_batches(text)
        words=' '.join(['longword']*30);self.assertEqual(' '.join(sentence_batches(words)),words)
    def test_backpressure_order_merge_hashes_offsets_and_cleanup(self):
        ident=self.state.start('One. Two. Three.',streaming=True)
        self.wait(lambda:len(self.state.get(ident)['chunks'])==2)
        time.sleep(.1);self.assertEqual(len(self.calls),2);self.assertTrue(self.state.busy)
        self.assertIsNone(self.state.start('Overlapping'))
        self.assertFalse(self.state.acknowledge(ident,1))
        chunks=[]
        for i in range(3):
            self.wait(lambda:bool(self.state.get(ident).get('chunks')))
            item=self.state.get(ident)['chunks'][0];chunks.append(item)
            self.assertEqual((item['index'],item['start_sample'],item['end_sample']),(i,i*2400,(i+1)*2400))
            self.assertTrue(self.state.acknowledge(ident,i))
            if i<2:self.assertTrue(self.state.acknowledge(ident,i))
        self.wait(lambda:not self.state.busy)
        final=self.state.get(ident);self.assertEqual(final['state'],'ready');clip=final['clip']
        self.assertAlmostEqual(clip['duration'],.3);self.assertEqual(clip['stream']['samples'],7200)
        self.assertEqual(clip['audio']['sha256'],audio_metadata(self.root/ident/'audio.wav')['sha256'])
        self.assertEqual([c['start_sample'] for c in clip['analysis']['sources']],[0,2400,4800])
        self.assertTrue(all(not (self.root/c['id']).exists() and self.state.get(c['id']) is None for c in chunks))
    def test_cancel_while_producer_is_backpressured_then_retry(self):
        ident=self.state.start('One. Two. Three.',streaming=True);self.wait(lambda:len(self.state.get(ident)['chunks'])==2)
        children=[c['id'] for c in self.state.get(ident)['chunks']];self.assertTrue(self.state.cancel(ident));self.wait(lambda:not self.state.busy)
        self.assertEqual(self.state.get(ident)['state'],'cancelled');self.assertFalse(self.state.streams)
        self.assertTrue(all(not (self.root/c).exists() and self.state.get(c) is None for c in children))
        retry=self.state.start('Retry');self.wait(lambda:not self.state.busy);self.assertEqual(self.state.get(retry)['state'],'ready')
    def test_disconnected_consumer_expires_and_frees_slot(self):
        with patch('neural_stream.CONSUMER_TIMEOUT',.1):
            ident=self.state.start('One. Two. Three.',streaming=True);self.wait(lambda:not self.state.busy)
        self.assertEqual(self.state.get(ident)['state'],'error');self.assertEqual(list(self.root.iterdir()),[])
    def test_get_returns_isolated_queue_snapshot(self):
        ident=self.state.start('One. Two. Three.',streaming=True);self.wait(lambda:bool(self.state.get(ident)['chunks']))
        result=self.state.get(ident);result['chunks'].clear();self.assertTrue(self.state.get(ident)['chunks'])
