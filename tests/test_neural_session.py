"""Model-free session integrity checks. Fixtures are tones, not neural speech."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_neural_clips import audio_metadata
from neural_session import validate_binding, text_hash


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.wav = Path(self.temp.name) / 'audio.wav'
        with wave.open(str(self.wav), 'wb') as w:
            w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            w.writeframes(struct.pack('<h', 5000) * 4800)
        self.rig = {'profile': 'test-only'}
        self.ident = 'a' * 32
        metrics = audio_metadata(self.wav)
        self.cues = {'metadata': {'duration': .2}, 'mouthCues': [{'start': 0, 'end': .2, 'value': 'A'}],
                     'provenance': {'audio_sha256': metrics['sha256']}}
        self.clip = {'id': self.ident, 'text': 'Test text', 'text_sha256': text_hash('Test text'),
                     'file': f'/sessions/{self.ident}/audio.wav', 'duration': .2,
                     'audio': metrics, 'cues': self.cues['mouthCues'], 'rig': self.rig}

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_binding(self):
        validate_binding(self.clip, self.wav, self.cues, self.rig)

    def test_another_recordings_cues_rejected(self):
        self.cues['provenance']['audio_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            validate_binding(self.clip, self.wav, self.cues, self.rig)

    def test_mutated_waveform_rejected(self):
        with self.wav.open('r+b') as f:
            f.seek(-2, 2); f.write(b'\x00\x00')
        with self.assertRaises(ValueError):
            validate_binding(self.clip, self.wav, self.cues, self.rig)

    def test_changed_text_rig_duration_identity_or_published_cues_rejected(self):
        changes = {'text': 'Not this text', 'rig': {'profile': 'other'}, 'duration': .3,
                   'id': '../escape', 'file': 'https://external.invalid/audio.wav',
                   'cues': [{'start': 0, 'end': .2, 'value': 'F'}]}
        for key, value in changes.items():
            bad = copy.deepcopy(self.clip); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_binding(bad, self.wav, self.cues, self.rig)

    def test_wrong_timeline_rejected_even_if_published_copy_matches(self):
        self.cues['mouthCues'][0]['end'] = .3
        with self.assertRaises(ValueError):
            validate_binding(self.clip, self.wav, self.cues, self.rig)


if __name__ == '__main__':
    unittest.main()
