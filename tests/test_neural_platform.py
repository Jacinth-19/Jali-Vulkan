"""Model-free Windows profile, extraction and cleanup contracts; no executable run."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_platform import analyzer_profile,archive_relative
import analyze_neural_clips as analyzer
from run_neural_ci import stop_server


class PlatformTests(unittest.TestCase):
    def test_windows_and_linux_have_distinct_pins_and_paths(self):
        win=analyzer_profile('win32','AMD64');linux=analyzer_profile('linux','x86_64')
        self.assertEqual(win['executable'],'rhubarb.exe');self.assertEqual(linux['executable'],'rhubarb')
        self.assertNotEqual(win['binary_sha256'],linux['binary_sha256'])
        self.assertNotEqual(win['cache'],linux['cache'])
        self.assertIn('github.com/DanielSWolf',win['url'])

    def test_unsupported_system_and_architecture_fail_closed(self):
        for system,machine in [('darwin','x86_64'),('win32','ARM64'),('linux','aarch64')]:
            with self.assertRaises(ValueError):analyzer_profile(system,machine)

    def test_traversal_drive_paths_and_dlls_not_admitted(self):
        spec=analyzer_profile('win32','AMD64');prefix=spec['marker']
        for name in (prefix+'../escape',prefix+'res/../../escape','C:/evil',prefix+'res\\evil'):
            with self.assertRaises(ValueError):archive_relative(name,spec)
        self.assertIsNone(archive_relative(prefix+'unknown.dll',spec))
        self.assertEqual(archive_relative(prefix+'res/model/data',spec),'res/model/data')

    def test_verified_zip_extracts_only_allowed_files_and_repairs_setup_cache(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);cache=root/'.cache/lipsync';cache.mkdir(parents=True)
            spec=analyzer_profile('win32','AMD64');spec['binary_sha256']=hashlib.sha256(b'fake unit fixture').hexdigest()
            archive=cache/'rhubarb-windows.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for p,b in [('rhubarb.exe',b'fake unit fixture'),('res/model/data',b'acoustic fixture'),('unknown.dll',b'excluded')]:z.writestr(spec['marker']+p,b)
            spec['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
            binary=cache/'rhubarb-windows/rhubarb.exe'
            with patch.object(analyzer,'ROOT',root),patch.object(analyzer,'analyzer_profile',return_value=spec),patch.object(analyzer,'analyzer_path',return_value=binary),patch.object(analyzer,'urlopen',side_effect=AssertionError('No download in unit tests')):
                self.assertEqual(analyzer.ensure_engine(),binary)
                self.assertFalse((binary.parent/'unknown.dll').exists())
                (binary.parent/'res/model/data').write_bytes(b'changed')
                analyzer.ensure_engine()
                self.assertEqual((binary.parent/'res/model/data').read_bytes(),b'acoustic fixture')
                archive.write_bytes(b'corrupt')
                with self.assertRaises(ValueError):analyzer.ensure_engine()

    def test_windows_cleanup_targets_only_our_process_tree(self):
        server=Mock(pid=12345);server.poll.return_value=None
        with patch('run_neural_ci.os.name','nt'),patch('run_neural_ci.subprocess.run') as run:
            stop_server(server)
        self.assertEqual(run.call_args.args[0],['taskkill','/PID','12345','/T','/F'])
        server.wait.assert_called_once_with(timeout=10)
