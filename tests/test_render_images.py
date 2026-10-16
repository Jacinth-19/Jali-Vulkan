"""Fast checks for committed real-render images and their point-in-time evidence."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ReadmeImageTests(unittest.TestCase):
    def setUp(self):self.evidence=json.loads((ROOT/'docs/images/render-evidence.json').read_text())

    def test_png_hashes_dimensions_and_small_repository_footprint(self):
        total=0;hashes=set()
        for record in self.evidence['images']:
            data=(ROOT/'docs/images'/record['file']).read_bytes();total+=len(data)
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',data[16:24]),(512,512))
            self.assertEqual(hashlib.sha256(data).hexdigest(),record['sha256']);hashes.add(record['sha256'])
        self.assertEqual(len(hashes),4);self.assertLess(total,2_000_000)

    def test_readme_embeds_all_four_images(self):
        text=(ROOT/'README.md').read_text()
        for record in self.evidence['images']:self.assertIn('docs/images/'+record['file'],text)
        self.assertIn('separate rendering paths',text)

    def test_evidence_does_not_conflate_webgl_with_native_or_claim_quality(self):
        human=[r for r in self.evidence['images'] if r['renderer']=='Three.js / WebGL']
        self.assertEqual({r['estimated_class'] for r in human},{'A','F','G'})
        for record in human:
            self.assertFalse(record['independent_phoneme_verification'])
            self.assertEqual(len(record['audio_sha256']),64)
        native=[r for r in self.evidence['images'] if r not in human]
        self.assertEqual(len(native),1);self.assertIn('NOT detailed MPFB',native[0]['model'])
        self.assertEqual(native[0]['metadata']['bones'],67)
        self.assertIsInstance(native[0]['metadata']['hardware_accelerated'],bool)
