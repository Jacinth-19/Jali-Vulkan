"""Model-free checks for WAV admission and downloadable test-pack integrity."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_test_pack import audio_metadata, seal_pack


class TestPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def wav(self, rate=16000, channels=1, width=2, silence=False, frames=2000):
        target = self.root / 'reference.wav'
        with wave.open(str(target), 'wb') as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(width)
            writer.setframerate(rate)
            if width == 2:
                values = [0 if silence else (1000 if i % 2 else -1000) for i in range(frames * channels)]
                writer.writeframes(struct.pack('<' + 'h' * len(values), *values))
            else:
                writer.writeframes(bytes([128]) * frames * channels)
        return target

    def test_pcm_duration_and_provenance(self):
        path = self.wav()
        data = audio_metadata(path)
        self.assertEqual(data['duration_seconds'], 0.125)
        self.assertEqual(data['sample_rate'], 16000)
        self.assertEqual(data['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertAlmostEqual(data['rms_dbfs'], -30.31, places=2)

    def test_reject_stereo(self):
        with self.assertRaises(ValueError):
            audio_metadata(self.wav(channels=2))

    def test_reject_eight_bit(self):
        with self.assertRaises(ValueError):
            audio_metadata(self.wav(width=1))

    def test_reject_silence(self):
        with self.assertRaises(ValueError):
            audio_metadata(self.wav(silence=True))

    def test_reject_low_sample_rate(self):
        with self.assertRaises(ValueError):
            audio_metadata(self.wav(rate=8000))

    def test_reject_empty_audio(self):
        with self.assertRaises(ValueError):
            audio_metadata(self.wav(frames=0))

    def test_zip_inventory_includes_later_evidence(self):
        pack = self.root / 'pack'
        pack.mkdir()
        (pack / 'index.html').write_text('Original synthetic fixture')
        archive = seal_pack(pack)
        original = json.loads((pack / 'checksums.json').read_text())
        self.assertNotIn('checksums.json', original)
        (pack / 'proof').mkdir()
        (pack / 'proof/check.json').write_text('{"result":"passed"}\n')
        seal_pack(pack)
        inventory = json.loads((pack / 'checksums.json').read_text())
        self.assertEqual(inventory['index.html'], original['index.html'])
        self.assertIn('proof/check.json', inventory)
        with zipfile.ZipFile(archive) as reader:
            self.assertEqual(reader.testzip(), None)
            self.assertIn('pack/proof/check.json', reader.namelist())
            self.assertEqual(reader.read('pack/index.html'), b'Original synthetic fixture')


if __name__ == '__main__':
    unittest.main()
