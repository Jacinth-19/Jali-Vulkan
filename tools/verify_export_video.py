"""Decode both streams and check actual decoded frame count, not just file existence."""
import json
from pathlib import Path
import re
import subprocess


def verify_export_video(movie, frame_file):
    import imageio_ffmpeg
    metadata = json.loads(Path(frame_file).read_text())
    decoded = subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-v', 'error',
        '-progress', 'pipe:1', '-nostats', '-i', str(movie),
        '-map', '0:v:0', '-map', '0:a:0', '-fps_mode', 'passthrough',
        '-f', 'null', '-'], check=True, capture_output=True, text=True, timeout=60)
    counts = re.findall(r'^frame=(\d+)\s*$', decoded.stdout, re.MULTILINE)
    expected = len(metadata['frames'])
    if not counts or int(counts[-1]) != expected or metadata['encoded_video_frames'] != expected:
        raise AssertionError(f'Decoded movie/frame timeline mismatch: {counts} vs {expected}')
    print(f'FFmpeg decoded both streams and all {expected} fixed-clock video frames')
