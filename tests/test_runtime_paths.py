"""Frozen renderer paths must not use the original checkout or writable CWD."""
from pathlib import Path
import sys
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
