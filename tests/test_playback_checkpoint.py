import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from array import array

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_playback_checkpoint import validate_inputs
from build_test_pack import audio_metadata
from prepare_kokoro_cpu import MODEL_SHA,VOICE_SHA


class CheckpointAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.review=self.root/'review';self.studio=self.root/'studio'
        (self.review/'sessions').mkdir(parents=True);(self.studio/'model').mkdir(parents=True)
        (self.studio/'viewer.js').write_bytes(b'viewer');(self.studio/'model/mpfb-head.glb').write_bytes(b'model')
        self.rig={'viewer_sha256':hashlib.sha256(b'viewer').hexdigest(),'model_sha256':hashlib.sha256(b'model').hexdigest()}
        (self.studio/'rig.json').write_text(json.dumps(self.rig))
        self.text='Public unit test.';self.corpus={'cases':[{'id':'case','text':self.text}]}
        wav=self.review/'sessions/case-audio.wav'
        with wave.open(str(wav),'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(24000);output.writeframes(array('h',[1000]*2400).tobytes())
        metrics=audio_metadata(wav);cue=[{'start':0,'end':.1,'value':'X'}]
        provenance={'audio_sha256':metrics['sha256'],'dialog_sha256':hashlib.sha256((self.text+'\n').encode()).hexdigest()}
        self.clip={'id':'a'*32,'text':self.text,'text_sha256':hashlib.sha256(self.text.encode()).hexdigest(),'rig':self.rig,
            'duration':.1,'file':'/sessions/'+'a'*32+'/audio.wav','audio':metrics,'cues':cue,'analysis':provenance,
            'tts':{'providers':['CPUExecutionProvider'],'model_sha256':MODEL_SHA,'voice_sha256':VOICE_SHA}}
        self.cues={'metadata':{'duration':.1},'mouthCues':cue,'provenance':provenance}
        self.write()

    def write(self):
        (self.review/'articulation.json').write_text(json.dumps({'sessions':[self.clip]}))
        (self.review/'sessions/case-manifest.json').write_text(json.dumps(self.clip))
        (self.review/'sessions/case-cues.json').write_text(json.dumps(self.cues))
        (self.review/'sessions/case-requested-text.txt').write_text(self.text)

    def check(self):
        return validate_inputs(self.review,self.studio,self.corpus)

    def test_valid_bound_synthetic_clip(self):
        self.assertEqual(self.check()[0]['sessions'][0]['id'],'a'*32)

    def test_private_or_changed_corpus_refused(self):
        self.corpus['cases'][0]['text']='Not the fixed public corpus'
        with self.assertRaises(ValueError):self.check()

    def test_tampered_rig_refused(self):
        (self.studio/'viewer.js').write_text('different viewer')
        with self.assertRaises(ValueError):self.check()

    def test_replaced_recording_refused(self):
        path=self.review/'sessions/case-audio.wav';raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
        with self.assertRaises(ValueError):self.check()

    def test_wrong_provider_or_voice_refused(self):
        self.clip['tts']['providers']=['CUDAExecutionProvider'];self.write()
        with self.assertRaises(ValueError):self.check()

    def test_wrong_dialog_refused(self):
        self.cues['provenance']['dialog_sha256']='incorrect';self.write()
        with self.assertRaises(ValueError):self.check()

    def test_wrong_manifest_refused(self):
        (self.review/'sessions/case-manifest.json').write_text('{}')
        with self.assertRaises(ValueError):self.check()
