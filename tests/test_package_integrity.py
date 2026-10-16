"""Model-free install corruption, path safety, and frozen-entry preflight tests."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from package_integrity import NAME,create_manifest,verify_installation,safe_name
import portable_entry


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'_internal').mkdir();(self.root/'app.exe').write_bytes(bytes(range(256)));(self.root/'_internal/model.bin').write_bytes(b'weights');create_manifest(self.root)
    def test_complete_is_read_only_and_deterministic(self):
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()};r=verify_installation(self.root)
        self.assertTrue(r['verified']);self.assertEqual(r['checked_files'],2);self.assertFalse(r['authenticity_verified'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
    def test_missing_modified_and_injected_file(self):
        (self.root/'app.exe').write_bytes(bytes(reversed(range(256))));(self.root/'_internal/model.bin').unlink();(self.root/'injected.dll').write_bytes(b'bad')
        r=verify_installation(self.root);self.assertFalse(r['verified']);self.assertEqual({x['kind'] for x in r['issues']},{'missing','modified','unexpected'});self.assertIn('new empty folder',r['repair'])
    def test_manifest_absent_malformed_wrong_schema_and_invalid_entries(self):
        for payload in (None,'{',json.dumps({'schema':'other'}),json.dumps({'schema':'jali-installation-integrity-v1','files':{'app.exe':{'size':True,'sha256':'g'*64}}})):
            with self.subTest(payload=payload):
                p=self.root/NAME
                if payload is None:p.unlink(missing_ok=True)
                else:p.write_text(payload)
                self.assertFalse(verify_installation(self.root)['verified'])
    def test_unsafe_names_are_rejected_before_hashing(self):
        for name in ('.','a\nb','a\x1fb','../out','/absolute','C:/app','a\\b','a//b','a/../b','a/./b','bad.','bad ','a:stream','a\0b','a?b'):
            self.assertFalse(safe_name(name),name)
        m=json.loads((self.root/NAME).read_text());m['files']['../outside']=m['files']['app.exe'];(self.root/NAME).write_text(json.dumps(m));self.assertFalse(verify_installation(self.root)['verified'])
    def test_case_colliding_manifest_rejected(self):
        m=json.loads((self.root/NAME).read_text());m['files']['APP.EXE']=m['files']['app.exe'];(self.root/NAME).write_text(json.dumps(m));self.assertFalse(verify_installation(self.root)['verified'])
    @unittest.skipIf(os.name=='nt','Windows symlink creation may require extra privilege')
    def test_linked_file_and_directory_fail_without_following_them(self):
        with tempfile.TemporaryDirectory() as outside:
            out=Path(outside);(out/'secret').write_bytes(b'secret')
            for target in (out/'secret',out):
                p=self.root/'linked';p.symlink_to(target,target_is_directory=target.is_dir())
                try:self.assertFalse(verify_installation(self.root)['verified'])
                finally:p.unlink()
    def test_frozen_verify_never_starts_server_or_clears_sessions(self):
        with patch.object(sys,'argv',['app','--verify-installation']),patch.object(sys,'executable',str(self.root/'app.exe')),patch.object(sys,'frozen',True,create=True),contextlib.redirect_stdout(io.StringIO()) as output:
            portable_entry.main()
        self.assertTrue(json.loads(output.getvalue())['verified'])
    def test_frozen_startup_fails_closed_before_server_import(self):
        (self.root/'app.exe').write_bytes(b'corrupted')
        with patch.object(sys,'argv',['app','--no-browser']),patch.object(sys,'executable',str(self.root/'app.exe')),patch.object(sys,'frozen',True,create=True),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:portable_entry.main()
        self.assertEqual(cm.exception.code,2)


if __name__=='__main__':unittest.main()
