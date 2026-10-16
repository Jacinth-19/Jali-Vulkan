"""Frozen renderer paths must not use the original checkout or writable CWD."""
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from runtime_paths import native_runtime


class RuntimeTests(unittest.TestCase):
    def test_frozen_native_paths_are_relative_to_immutable_assets(self):
        with patch.object(sys,'frozen',True,create=True):
            binary,shaders=native_runtime(Path('/relocated/_internal'))
        self.assertEqual(binary,Path('/relocated/_internal/native/jali_rich.exe'));self.assertEqual(shaders,Path('/relocated/_internal/native/shaders'))
    def test_developer_path_uses_selected_platform_not_assumed_linux(self):
        with patch.object(sys,'frozen',False,create=True),patch.object(sys,'platform','win32'):
            binary,shaders=native_runtime(Path('/repo'))
        self.assertEqual(binary,Path('/repo/build-live/jali_rich.exe'));self.assertIsNone(shaders)


class NativeShapeRuntimeTests(unittest.TestCase):
    def test_source_runtime_does_not_launch_node(self):
        from neural_visemes import shared_shapes
        with patch('subprocess.check_output',side_effect=AssertionError('No runtime subprocess')):
            self.assertEqual(set(shared_shapes()),set('ABCDEFGHX'))
    def test_frozen_table_bound_to_rig_without_source_tree_or_node(self):
        from neural_visemes import shared_shapes
        source=Path(__file__).resolve().parents[1]/'web/neural-head/native-shapes.json';data=json.loads(source.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);assets=root/'artifacts/neural-studio';assets.mkdir(parents=True);(assets/'native-shapes.json').write_text(json.dumps(data));rig=assets/'rig.json';rig.write_text(json.dumps({'retarget_sha256':data['retarget_sha256']}))
            with patch('neural_visemes.ROOT',root),patch.object(sys,'frozen',True,create=True),patch('subprocess.check_output',side_effect=AssertionError('No runtime Node')):
                self.assertEqual(set(shared_shapes()),set('ABCDEFGHX'))
                rig.write_text(json.dumps({'retarget_sha256':'0'*64}))
                with self.assertRaises(ValueError):shared_shapes()
