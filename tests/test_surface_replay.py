import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from run_surface_replay import require_appearance_only_change

class AppearanceReplay(unittest.TestCase):
    def test_only_explicit_viewer_change_allowed(self):
        old={'viewer_sha256':'old','model_sha256':'mesh','retarget_sha256':'map','profile':'same'}
        require_appearance_only_change(old,{**old,'viewer_sha256':'new'})
    def test_geometry_mapping_profile_changes_rejected(self):
        old={'viewer_sha256':'old','model_sha256':'mesh','retarget_sha256':'map','profile':'same'}
        for field in ['model_sha256','retarget_sha256','profile']:
            with self.assertRaises(ValueError):require_appearance_only_change(old,{**old,'viewer_sha256':'new',field:'changed'})
    def test_unchanged_or_missing_identity_rejected(self):
        old={'viewer_sha256':'old','model_sha256':'mesh'}
        with self.assertRaises(ValueError):require_appearance_only_change(old,old)
        with self.assertRaises(ValueError):require_appearance_only_change(old,{'viewer_sha256':'new'})
