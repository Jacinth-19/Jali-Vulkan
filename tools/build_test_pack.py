#!/usr/bin/env python3
"""Package the original GLB, existing external voice references, and a native baseline.

Run on the supported Linux native development environment after bootstrap:
  .venv/bin/python tools/build_test_pack.py --software-vulkan

The three stock neural WAVs must already exist in OUTPUT/audio. This script does
not download models, clone a speaker, synthesize those WAVs, or invent alignment.
Generated deliverables stay under ignored artifacts/, never in source control.
"""
import argparse
from array import array
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave
import zipfile

from live_session import LiveWorker
from render_session import ROOT

REFERENCES = [
    ('01-normal-speech.wav', 'Natural speech',
     'Hello, I’m Jali. This is our first talking character test. I can speak clearly, pause naturally, and change the shape of my mouth. We are building this step by step, on a normal computer.',
     ['clarity', 'phrase breaks', 'pacing']),
    ('02-lip-closures.wav', 'Lip closures',
     'Mama made blueberry muffins. Papa packed a big paper bag. Bob bought pink balloons. Please bring my blue backpack. Mama. Papa. Baby. Maybe.',
     ['M/P/B closures', 'consonant transitions']),
    ('03-rounded-vowels.wav', 'Vowels and rounding',
     'Blue moon. Cool water. Who will you choose? We will see you soon. A bright smile, a wide open mouth, and a soft, slow goodbye. Oh. Ooh. Ah. Ee.',
     ['rounded vowels', 'open vowels', 'vowel transitions']),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audio_metadata(path):
    with wave.open(str(path), 'rb') as reader:
        if reader.getnchannels() != 1 or reader.getsampwidth() != 2 or reader.getcomptype() != 'NONE':
            raise ValueError(f'{path}: expected uncompressed mono PCM16')
        rate = reader.getframerate()
        count = reader.getnframes()
        if not 16000 <= rate <= 48000 or not rate // 10 <= count <= rate * 60:
            raise ValueError(f'{path}: invalid sample rate or duration')
        samples = array('h', reader.readframes(count))
    if sys.byteorder != 'little':
        samples.byteswap()
    if len(samples) != count:
        raise ValueError(f'{path}: truncated PCM')
    peak = max(abs(v) for v in samples) / 32768
    rms = math.sqrt(sum(v * v for v in samples) / count) / 32768
    if peak < 0.001 or rms <= 0:
        raise ValueError(f'{path}: silent or nearly silent audio')
    return {'sample_rate': rate, 'channels': 1, 'sample_width_bits': 16,
            'duration_seconds': count / rate, 'peak_amplitude': peak,
            'rms_dbfs': round(20 * math.log10(rms), 2), 'sha256': sha256(path)}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def seal_pack(output):
    """Update the checksum inventory and ZIP after adding browser-test evidence."""
    files = {path.relative_to(output).as_posix(): sha256(path)
             for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'checksums.json'}
    write_json(output / 'checksums.json', files)
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output.parent).as_posix())
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/face-voice-test-pack')
    parser.add_argument('--software-vulkan', action='store_true')
    parser.add_argument('--seal-only', action='store_true', help='Update checksums/ZIP without rerendering')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.seal_only:
        if not (output / 'manifest.json').is_file():
            parser.error('No completed pack manifest found')
        print(seal_pack(output))
        return
    references = []
    for filename, title, text, checks in REFERENCES:
        path = output / 'audio' / filename
        references.append({'file': f'audio/{filename}', 'title': title, 'requested_text': text,
                           'intended_checks': checks, 'alignment': None,
                           'generation': 'Arena speech tool; selected stock synthetic voice; not local inference',
                           **audio_metadata(path)})
    for name in ('model', 'poses', 'baseline', 'proof'):
        (output / name).mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'rig-viewer.js'):
        shutil.copy2(ROOT / 'web/test-pack' / name, output / name)
    asset = ROOT / 'build-live/assets/android.glb'
    shutil.copy2(asset, output / 'model/jali-android.glb')
    shutil.copy2(ROOT / 'tools/make_character.py', output / 'model/make_character.py')
    (output / 'rig-data.js').write_text('window.JALI_RIG_BASE64=' + json.dumps(base64.b64encode(asset.read_bytes()).decode()) + ';\n')
    validator = subprocess.run(['node', 'tools/validate_character.cjs', str(asset)], cwd=ROOT,
                               capture_output=True, text=True, check=True)
    (output / 'proof/gltf-validation.json').write_text(validator.stdout)

    worker = LiveWorker('Hello. Mama. Papa. Blue moon. See you soon.', software=args.software_vulkan)
    try:
        metadata = {k: v for k, v in worker.metadata.items() if k not in ('id', 'audio_url', 'cues_url')}
        cues = json.loads((worker.directory / 'phonemes.json').read_text())
        duration = metadata['duration_seconds']
        targets = {'rest': duration,
                   'closure': next(c['seconds'] for c in cues if c['symbol'] in ('m', 'p', 'b')),
                   'open': next(c['seconds'] for c in cues if c['symbol'] in ('A:', 'a', 'a#', 'aI')),
                   'round': next(c['seconds'] for c in cues if c['symbol'] in ('u:', 'U', 'O:', 'oU'))}
        from PIL import Image
        import io
        for name, seconds in targets.items():
            jpeg, _ = worker.frame(seconds)
            with Image.open(io.BytesIO(jpeg)) as image:
                image.save(output / 'poses' / f'{name}.png')
        shutil.copy2(worker.directory / 'session.wav', output / 'baseline/04-local-phoneme-baseline.wav')
        shutil.copy2(worker.directory / 'phonemes.json', output / 'baseline/phonemes.json')
        write_json(output / 'baseline/native-metadata.json', metadata)
        write_json(output / 'poses/timestamps.json', targets)
        # The baseline video uses ONLY the eSpeak WAV and its own timing events.
        # Never attach the externally generated neural references to these poses.
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory(prefix='jali-test-frames-') as directory:
            frames = Path(directory)
            fps = 20
            for index in range(math.ceil(duration * fps)):
                jpeg, _ = worker.frame(min(index / fps, duration))
                (frames / f'frame-{index:04d}.jpg').write_bytes(jpeg)
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y',
                            '-framerate', str(fps), '-i', str(frames / 'frame-%04d.jpg'),
                            '-i', str(output / 'baseline/04-local-phoneme-baseline.wav'),
                            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart',
                            str(output / 'baseline/04-local-phoneme-baseline.mp4')], check=True, timeout=60)
    finally:
        worker.close()
    write_json(output / 'manifest.json', {
        'schema': 1, 'purpose': 'Personal CPU-first face and voice evaluation',
        'target': 'Windows, Intel Core i5 10th-generation U-series, 16 GB RAM; not benchmarked on that device',
        'character': {'file': 'model/jali-android.glb', 'sha256': sha256(asset),
                      'origin': 'Original procedural Jali android, not a third-party or scanned human face',
                      'vertices': metadata['vertices'], 'triangles': metadata['triangles'],
                      'bones': ['Root', 'Jaw'], 'morph_targets': ['jawOpen', 'mouthRound', 'mouthClose']},
        'voice_references': references,
        'baseline': {'file': 'baseline/04-local-phoneme-baseline.mp4',
                     'voice': 'Local built-in eSpeak, NOT the neural reference voice',
                     'alignment': 'Actual eSpeak phoneme timing events', 'renderer': metadata['device'],
                     'hardware_accelerated': metadata['hardware_accelerated']},
        'inspector': 'WebGL morph-before-skin inspector; not the native Vulkan renderer',
        'limitations': ['External reference voice is not a self-hosted or cloned model.',
                        'Neural references do not yet have forced phoneme alignment.',
                        'Manual inspector does not automatically lip-sync neural clips.',
                        'Windows native engine and target-laptop performance are not validated.'],
    })
    (output / 'README.txt').write_text('''JALI — FACE AND VOICE TEST PACK 001

WINDOWS QUICK START
1. Extract the ZIP completely. Do not open index.html from inside the ZIP viewer.
2. Double-click index.html in Edge, Chrome or Firefox. No Python or server is needed.
3. Rotate the original GLB face and try Rest, Ah, Ooh, and M/P/B.
4. Listen to the three WAVs and check clarity, pacing, and consonants/vowels.
5. Play the separate local baseline video. Inspect baseline/phonemes.json.

If WebGL 2 is unavailable, the page shows a native-rendered rest image instead.
You can still play all WAVs and the MP4 directly in a desktop media player.
The GLB can also be imported in Blender for bone/shape-key inspection. No
Blender import/export round-trip guarantee is made by this pack.

WHAT IS ACTUALLY INCLUDED
- Original Jali android: 11,392 vertices, 20,736 triangles, Root/Jaw bones,
  blended skin weights and jawOpen/mouthRound/mouthClose position morphs.
- Three mono PCM16, 44.1 kHz stock neural-voice references generated with the
  Arena speech tool and a selected voice. See manifest.json for exact requested
  text, measured durations, PCM checks, hashes and provenance.
- A different eSpeak voice in the baseline video: actual local synthesis,
  actual phoneme events and native Vulkan mesh rendering on software Vulkan.
- Four native-rendered pose PNGs and the official glTF Validator report.
- A standalone WebGL rig inspector using the same model and jaw convention.
- The original model generator. The complete native engine is in the repo.

IMPORTANT LIMITS
The neural clips are NOT proof of local neural inference, voice cloning, or
neural lip-sync. Their phoneme timing is not aligned. No eSpeak timestamps
have been copied onto them. The inspector is manual, not an automatic facial
solver. The separate baseline video is the only aligned playback example.
The external stock voice's downloadable model/runtime is not included; we
cannot promise that this exact voice can be reproduced locally or at no cost.
Generated speech is synthetic, not a recording of a real participant here.
The original model does not depend on purchased/downloaded human face art.
No project-wide distribution license has been selected; do not treat this
pack as a license grant for third-party model/runtime redistribution.

YOUR COMPUTER
Your Windows / i5 10th-gen U / 16 GB machine is a reasonable CPU-first target,
not a measured performance guarantee. This standalone pack is browser-only.
For the native engine, Linux is the tested environment; WSL2 is a possible
Windows development route, but has not been tested on your laptop. Native
Windows pipe transport is not currently supported by the Linux preview code.

NEXT ENGINE MILESTONE
Choose and test a permitted locally runnable neural voice on CPU. Obtain true
phoneme alignment for its own audio. Feed that timing into our existing face
renderer. Then measure speed and quality on the target laptop. Use only your
own authorized recording if we subsequently add your voice likeness.
''', encoding='utf-8')
    archive = seal_pack(output)
    print(f'Test pack ready: {archive} ({archive.stat().st_size:,} bytes)')
    print(json.dumps({'clips': [{k: c[k] for k in ('file', 'duration_seconds', 'rms_dbfs')} for c in references],
                      'native_device': metadata['device']}, indent=2))


if __name__ == '__main__':
    main()
