"""Cold asset transfer must preserve binary bytes without gh raw-text transforms."""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_neural_head import github_file


class GitHubAssetTests(unittest.TestCase):
    def test_small_file_decoded_from_json(self):
        encoded = base64.b64encode(b'license\n').decode() + '\n'
        with patch('build_neural_head.subprocess.check_output', return_value=json.dumps({'encoding':'base64','content':encoded}).encode()) as run:
            self.assertEqual(github_file('repos/owner/repo/contents/LICENSE?ref=pinned'), b'license\n')
            self.assertNotIn('Accept: application/vnd.github.raw+json', run.call_args.args[0])

    def test_large_file_uses_blob_and_preserves_non_utf8(self):
        data = b'glTF\x00\xff\x80\r\n\x1b'
        with patch('build_neural_head.subprocess.check_output', side_effect=[
            json.dumps({'encoding':'none','sha':'a'*40}).encode(),
            json.dumps({'encoding':'base64','content':base64.b64encode(data).decode()}).encode()
        ]) as run:
            self.assertEqual(github_file('repos/owner/repo/contents/head.glb?ref=pinned'), data)
            self.assertEqual(run.call_args.args[0], ['gh','api','repos/owner/repo/git/blobs/'+'a'*40])

    def test_reject_bad_large_file_metadata(self):
        with patch('build_neural_head.subprocess.check_output', return_value=b'{"encoding":"none","sha":"../../bad"}'):
            with self.assertRaises(ValueError):
                github_file('repos/owner/repo/contents/head.glb')

    def test_reject_unknown_encoding(self):
        with patch('build_neural_head.subprocess.check_output', return_value=b'{"encoding":"mystery","content":"bad"}'):
            with self.assertRaises(ValueError):
                github_file('repos/owner/repo/contents/head.glb')
