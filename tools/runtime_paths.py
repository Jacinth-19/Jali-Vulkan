"""Explicit immutable asset location for source and frozen portable builds."""
from pathlib import Path
import sys


def asset_root():
    return Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]


ASSET_ROOT=asset_root()


def speech_worker_command(root,args):
    if getattr(sys,'frozen',False):return [sys.executable,'--speech-worker',*args]
    return [sys.executable,str(root/'tools/local_neural_speech.py'),*args]


def native_runtime(root=ASSET_ROOT):
    """Explicit packaged paths; never depend on the build machine's absolute paths."""
    if getattr(sys,'frozen',False):return root/'native/jali_rich.exe',root/'native/shaders'
    return root/('build-live/jali_rich.exe' if sys.platform=='win32' else 'build-live/jali_rich'),None
