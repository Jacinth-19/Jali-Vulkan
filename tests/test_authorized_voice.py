import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from authorized_voice import FILES, sha256, synthesize, validate_grant


class VoiceGrantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.manifest = self.root / 'grant.json'
        with wave.open(str(self.root / 'reference.wav'), 'wb') as audio:
            audio.setparams((1,2,16000,0,'NONE','not compressed')); audio.writeframes(b'\0\0'*48000)
        (self.root/'model').mkdir()
        for name in FILES: (self.root/'model'/name).write_bytes(b'unit-test-placeholder-not-a-model')
        self.grant = {'schema':1,'consent_id':'test-admission-only','subject_id':'unit-fixture','status':'active',
                      'scopes':['local-voice-synthesis'],'expires_at':'2100-01-01T00:00:00Z',
                      'reference':{'path':'reference.wav','sha256':sha256(self.root/'reference.wav')},
                      'model':{'directory':'model','license_reviewed':True,
                               'sha256':{name:sha256(self.root/'model'/name) for name in FILES}}}
        self.save()

    def save(self): self.manifest.write_text(json.dumps(self.grant))

    def test_admission_does_not_import_or_run_a_model(self):
        grant, reference, model = validate_grant(self.manifest)
        self.assertEqual(grant['consent_id'], 'test-admission-only')
        self.assertEqual(reference, self.root/'reference.wav')
        self.assertEqual(model, self.root/'model')

    def test_revoked_expired_or_wrong_scope_fails_before_inference(self):
        original=copy.deepcopy(self.grant)
        for patch in ({'status':'revoked'},{'scopes':[]},{'scopes':'local-voice-synthesis'},
                      {'expires_at':'2000-01-01T00:00:00Z'},{'expires_at':'2100-01-01T00:00:00'}):
            self.grant=copy.deepcopy(original);self.grant.update(patch);self.save()
            with self.assertRaises(ValueError): synthesize(self.manifest,'Hello',self.root/'output.wav')
            self.assertFalse((self.root/'output.wav').exists())

    def test_changed_reference_rejected(self):
        (self.root/'reference.wav').write_bytes(b'changed')
        with self.assertRaises(ValueError): validate_grant(self.manifest)

    def test_model_hash_or_license_rejected(self):
        self.grant['model']['license_reviewed']=False;self.save()
        with self.assertRaises(ValueError): validate_grant(self.manifest)
        self.grant['model']['license_reviewed']=True;self.save()
        (self.root/'model'/FILES[0]).write_bytes(b'changed')
        with self.assertRaises(ValueError): validate_grant(self.manifest)

    def test_pickle_conditionals_not_loaded(self):
        (self.root/'model/conds.pt').write_bytes(b'not-a-trusted-pickle')
        with self.assertRaises(ValueError): validate_grant(self.manifest)

    def test_invalid_text_rejected(self):
        for text in ('',' ','x'*241,'a\0b'):
            with self.assertRaises(ValueError): synthesize(self.manifest,text,self.root/'output.wav')
