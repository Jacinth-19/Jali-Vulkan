"""Build-only canonical correspondence checks; real asset audit runs in Actions."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_makehuman_male import canonical_map, prepare

@unittest.skipUnless(importlib.util.find_spec('scipy') and importlib.util.find_spec('numpy'),'Optional male-build SciPy dependency')
class MaleCorrespondence(unittest.TestCase):
    def fixture(self,root):
        import numpy as np
        p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,1,1],[2,1,0]],dtype=float)
        uv=np.array([[.1,.1],[.2,.2],[.3,.3],[.4,.4],[.1,.1],[.6,.6]])
        obj=Path(root)/'base.obj'
        obj.write_text(''.join('v '+' '.join(map(str,v))+'\n' for v in p)+''.join('vt '+' '.join(map(str,v))+'\n' for v in uv)+'f 1/1 2/2 3/3\nf 3/3 4/4 5/5\nf 4/4 5/5 6/6\n')
        return obj,p,uv
    def test_uv_flip_exact_join_and_ambiguous_rest_space_resolution(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as root:
            obj,p,uv=self.fixture(root)
            coords=uv.copy();coords[:,1]=1-coords[:,1]
            result,count,ambiguous=canonical_map(obj,coords,p*.1+[0,.85,0])
            np.testing.assert_array_equal(result,[0,1,2,3,4,5]);self.assertEqual(count,6);self.assertEqual(ambiguous,2)
    def test_unknown_uvs_fail_closed(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as root:
            obj,p,uv=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'correspondence failed'):
                canonical_map(obj,np.ones_like(uv)*.99,p)
    def test_existing_character_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            marker=Path(root)/'keep';marker.write_text('existing character')
            with self.assertRaisesRegex(ValueError,'never overwritten'):prepare(root)
            self.assertEqual(marker.read_text(),'existing character')
