"""Cross-platform PNG/GLB byte differences never relax corpus rig identity."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_native_ci as ci


class PreparedReferenceTests(unittest.TestCase):
    def test_restore_exact_producer_rig_after_platform_local_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);model=root/'artifacts/neural-head-demo/model/mpfb-head.glb';model.parent.mkdir(parents=True);reference=b'exact verified producer bytes';model.write_bytes(reference)
            review=root/'review';review.mkdir();rig={'model_sha256':hashlib.sha256(reference).hexdigest()};(review/'articulation.json').write_text(json.dumps({'sessions':[{'rig':rig}]*3}))
            def local_prepare():model.write_bytes(b'platform dependent PNG encoding')
            def native(source,output):self.assertEqual(source.read_bytes(),reference)
            with patch.object(ci,'ROOT',root),patch.object(ci,'prepare_model',side_effect=local_prepare),patch.object(ci,'native',side_effect=native) as n,patch.object(ci,'presentation') as p,patch.object(ci,'compare'):
                ci.prepare(review)
            n.assert_called_once();p.assert_called_once_with(prepare_speech=False);self.assertEqual(model.read_bytes(),reference)
    def test_staged_wrong_model_rejected_before_source_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);model=root/'artifacts/neural-head-demo/model/mpfb-head.glb';model.parent.mkdir(parents=True);model.write_bytes(b'wrong')
            review=root/'review';review.mkdir();(review/'articulation.json').write_text(json.dumps({'sessions':[{'rig':{'model_sha256':'0'*64}}]*3}))
            with patch.object(ci,'ROOT',root),patch.object(ci,'prepare_model') as p:
                with self.assertRaisesRegex(ValueError,'Staged prepared rig differs'):ci.prepare(review)
            p.assert_not_called()
