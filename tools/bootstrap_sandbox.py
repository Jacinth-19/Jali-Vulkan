#!/usr/bin/env python3
"""Opt-in Linux x86_64 / Python 3.11 development runtime; no assets enter Git.

Normal developer machines should use distribution Vulkan/eSpeak development packages.
This fallback extracts software Vulkan from a pinned npm package, and eSpeak from a
pinned wheel. It does not install or launch Chromium, a voice model, or a cloud client.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/deps"
ARCHIVES = [
    ("tinygltf.tar.gz", "https://codeload.github.com/syoyo/tinygltf/tar.gz/refs/tags/v2.9.3",
     "c34443de2e9afaaf005713f69f5b061101a24ab2e9ee4021d882ac1d7983dbc0"),
    ("headers.tar.gz", "https://codeload.github.com/KhronosGroup/Vulkan-Headers/tar.gz/refs/tags/v1.3.290",
     "f38a653bf93cab7a2a229a53d2d53b1cba9a2819e4c0a7de13c54085bde9bcf5"),
    ("espeak.tar.gz", "https://codeload.github.com/espeak-ng/espeak-ng/tar.gz/refs/tags/1.51",
     "f0e028f695a8241c4fa90df7a8c8c5d68dcadbdbc91e758a97e594bbb0a3bdbf"),
]
WHEEL = "piper_phonemize-1.1.0-cp311-cp311-manylinux_2_28_x86_64.whl"
WHEEL_SHA = "c1062e00c94835e9115df7ce1d7b3b5c40c6d845cd70b2c121954faf5b8d23c7"


def checked_download(name, url, digest):
    path = CACHE / name
    if not path.is_file():
        print(f"Downloading {name}", flush=True)
        with urlopen(url, timeout=60) as source, path.open("wb") as target:
            shutil.copyfileobj(source, target)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Checksum mismatch: {path}; remove the file and retry")
    return path


def main():
    if sys.version_info[:2] != (3, 11) or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("This sandbox helper requires Linux x86_64 and Python 3.11; use system dependencies otherwise")
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Run in a virtual environment: python3 -m venv .venv; .venv/bin/python tools/bootstrap_sandbox.py")
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "cmake==3.31.6", "imageio-ffmpeg==0.6.0", "pillow==11.3.0"], check=True)
    subprocess.run(["npm", "ci", "--prefix", str(ROOT / "tools"), "--ignore-scripts"], check=True)
    for name, url, digest in ARCHIVES:
        archive = checked_download(name, url, digest)
        with tarfile.open(archive) as tar:
            # eSpeak contains an unused compatibility-header symlink; omit links.
            members = [member for member in tar.getmembers() if not member.issym() and not member.islnk()]
            for member in members:
                destination = (CACHE / member.name).resolve()
                if not destination.is_relative_to(CACHE.resolve()) or not (member.isfile() or member.isdir()):
                    raise RuntimeError("Unsafe source archive entry")
            tar.extractall(CACHE, members=members)
    with urlopen("https://pypi.org/pypi/piper-phonemize/1.1.0/json", timeout=30) as response:
        metadata = json.load(response)
    artifact = next(item for item in metadata["urls"] if item["filename"] == WHEEL)
    wheel = checked_download(WHEEL, artifact["url"], WHEEL_SHA)
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if not (CACHE / "piper" / name).resolve().is_relative_to((CACHE / "piper").resolve()):
                raise RuntimeError("Unsafe wheel path")
        archive.extractall(CACHE / "piper")
    runtime = ROOT / ".cache/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    script = """
const fs=require('node:fs'),zlib=require('node:zlib');
fs.writeFileSync('.cache/runtime/swiftshader.tar',zlib.brotliDecompressSync(
  fs.readFileSync('tools/node_modules/@sparticuz/chromium/bin/swiftshader.tar.br')));
"""
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True)
    with tarfile.open(runtime / "swiftshader.tar") as archive:
        for member in archive.getmembers():
            if member.name not in {"libEGL.so", "libGLESv2.so", "libvk_swiftshader.so", "libvulkan.so.1", "vk_swiftshader_icd.json"} or not member.isfile():
                raise RuntimeError("Unexpected SwiftShader archive entry")
        archive.extractall(runtime)
    espeak_library = next((CACHE / "piper/piper_phonemize.libs").glob("libespeak-ng*.so.*"))
    cmake = str(Path(sys.executable).parent / "cmake")
    subprocess.run([cmake, "-S", str(ROOT), "-B", str(ROOT / "build-live"), "-DCMAKE_BUILD_TYPE=Release",
                    "-DJALI_ENABLE_ESPEAK=ON", "-DJALI_ENABLE_VULKAN=ON",
                    f"-DESPEAK_INCLUDE_DIR={CACHE / 'espeak-ng-1.51/src/include'}",
                    f"-DESPEAK_LIBRARY={espeak_library}",
                    f"-DVulkan_INCLUDE_DIR={CACHE / 'Vulkan-Headers-1.3.290/include'}",
                    f"-DVulkan_LIBRARY={runtime / 'libvulkan.so.1'}"], check=True)
    subprocess.run([cmake, "--build", str(ROOT / "build-live"), "--parallel", "2"], check=True)
    env = os.environ.copy()
    env["JALI_ESPEAK_DATA"] = str(CACHE / "piper/piper_phonemize")
    env["VK_ICD_FILENAMES"] = str(runtime / "vk_swiftshader_icd.json")
    subprocess.run([str(Path(sys.executable).parent / "ctest"), "--test-dir", str(ROOT / "build-live"), "--output-on-failure"], env=env, check=True)
    print("Ready. Run .venv/bin/python tools/preview_server.py --software-vulkan for live phoneme-driven rendering")


if __name__ == "__main__":
    main()
