#!/usr/bin/env python3
"""Generate real local speech, native Vulkan frames, then a browser-playable MP4."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from runtime_paths import ASSET_ROOT as ROOT


def runtime_environment(software=False):
    env = os.environ.copy()
    data = ROOT / ".cache/deps/piper/piper_phonemize"
    if data.is_dir():
        env.setdefault("JALI_ESPEAK_DATA", str(data))
    if software:
        icd = ROOT / ".cache/runtime/vk_swiftshader_icd.json"
        if not icd.is_file():
            raise RuntimeError("SwiftShader is missing; run tools/bootstrap_sandbox.py first")
        env["VK_ICD_FILENAMES"] = str(icd)
    return env


def run(command, env=None, timeout=120):
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "subprocess failed")[-2000:])
    return result


def render_session(output, text, binary=None, software=False, size=512, fps=24, on_stage=None):
    import imageio_ffmpeg
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 240 or "\0" in text:
        raise ValueError("Enter 1-240 UTF-8 bytes of nonblank text without NUL")
    output = Path(output).resolve()
    binary = Path(binary or ROOT / "build-live/jali_demo").resolve()
    if not binary.is_file():
        raise RuntimeError("Build the eSpeak and Vulkan backends first (see docs/running-demo.md)")
    env = runtime_environment(software)
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    raw = output / "frames.rgba"
    try:
        if on_stage:
            on_stage("Synthesizing speech and rendering Vulkan frames")
        run([str(binary), "--voice", "espeak", "--renderer", "vulkan", "--text", text,
             "--output", str(output), "--size", str(size), "--fps", str(fps)], env=env)
        render_seconds = time.monotonic() - start
        meta = json.loads((output / "session.json").read_text())
        if on_stage:
            on_stage("Encoding synchronized playback")
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgba",
             "-video_size", f'{meta["width"]}x{meta["height"]}', "-framerate", str(meta["fps"]),
             "-i", str(raw), "-i", str(output / "session.wav"), "-c:v", "libx264", "-preset", "fast",
             "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
             "-shortest", str(output / "session.mp4")])
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(output / "session.mp4"),
             "-frames:v", "1", str(output / "poster.jpg")])
        meta.update(text=text, render_seconds=round(render_seconds, 3),
                    total_seconds=round(time.monotonic() - start, 3),
                    metrics=json.loads((output / "metrics.json").read_text()))
        (output / "session.json").write_text(json.dumps(meta, indent=2) + "\n")
        return meta
    finally:
        raw.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="Welcome to Jali. My voice is synthesized locally, and my face is rendered with Vulkan.")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/live-demo")
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--software-vulkan", action="store_true")
    args = parser.parse_args()
    print(json.dumps(render_session(args.output, args.text, args.binary, args.software_vulkan), indent=2))


if __name__ == "__main__":
    main()
