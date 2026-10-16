#!/usr/bin/env python3
"""Build a free-model browser lip-sync demo from the existing stock neural WAVs.

Developer build: Linux/Python 3.11, Node tools and gh; no GPU or voice synthesis.
Generated assets stay ignored. The finished ZIP runs without these build tools.
"""
import argparse
import base64
import io
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

from analyze_neural_clips import analyze, digest, validate_timeline, ARCHIVE_URL, ARCHIVE_SHA, BINARY_SHA
from build_test_pack import REFERENCES, ROOT, audio_metadata, seal_pack

SOURCE_COMMIT = '2afe6d79779313db8909badebf46f9805a6c7b70'
SOURCE_SHA = '63c645a2a863b9972e9a9c2ed576a1de4c390b8475508e1473e69c87a3ee299c'
OUTPUT = ROOT / 'artifacts/neural-head-demo'
CACHE = ROOT / '.cache/lipsync'


def github_file(path):
    return subprocess.check_output(['gh', 'api', path, '-H', 'Accept: application/vnd.github.raw+json'], timeout=120)


def prepare_model():
    from PIL import Image
    CACHE.mkdir(parents=True, exist_ok=True)
    original = CACHE / 'mpfb.glb'
    if not original.is_file():
        original.write_bytes(github_file(f'repos/met4citizen/TalkingHead/contents/avatars/mpfb.glb?ref={SOURCE_COMMIT}'))
    if digest(original) != SOURCE_SHA:
        raise ValueError('Source character hash mismatch')
    raw = original.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    model = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
    texture_dir = CACHE / 'textures'
    texture_dir.mkdir(exist_ok=True)
    for index, texture in enumerate(model['images']):
        view = model['bufferViews'][texture['bufferView']]
        start = view.get('byteOffset', 0)
        with Image.open(io.BytesIO(binary[start:start + view['byteLength']])) as image:
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            image.save(texture_dir / f'{index}.png', optimize=True)
    subprocess.run(['node', 'tools/prepare_head.cjs'], cwd=ROOT, check=True, timeout=120)
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal-only', action='store_true')
    parser.add_argument('--reuse-cues', action='store_true', help='Reuse only cues with matching input WAV hashes')
    args = parser.parse_args()
    if args.seal_only:
        if not (OUTPUT / 'manifest.json').is_file():
            parser.error('No completed demo found')
        for relative in ('index.html', 'viewer.js', 'demo-data.js', 'rendered-lip-closures.mp4', 'poster.jpg',
                         'proof/video-export.json', 'proof/browser-check.json', 'proof/decoded-model-validation.json'):
            if not (OUTPUT / relative).is_file():
                raise ValueError(f'Cannot seal an unfinished demo: {relative}')
        manifest = json.loads((OUTPUT / 'manifest.json').read_text())
        video = json.loads((OUTPUT / 'proof/video-export.json').read_text())
        reports = json.loads((OUTPUT / 'proof/browser-check.json').read_text())
        if {r['mode'] for r in reports if r['passed']} != {'HTTP', 'offline file'}:
            raise ValueError('Both browser modes must pass before packaging')
        expected = {'mp4_sha256': digest(OUTPUT / 'rendered-lip-closures.mp4'),
                    'audio_sha256': digest(OUTPUT / 'audio/02-lip-closures.wav'),
                    'model_sha256': digest(OUTPUT / 'model/mpfb-head.glb'),
                    'viewer_sha256': digest(OUTPUT / 'viewer.js')}
        for key, value in expected.items():
            if video.get(key) != value:
                raise ValueError(f'Stale video evidence: {key}; rerun EXPORT_VIDEO=1 smoke test')
        cue_hash = subprocess.check_output(['node', '-e',
            "const fs=require('fs'),crypto=require('crypto'); const cues=JSON.parse(fs.readFileSync(process.argv[1])).mouthCues; process.stdout.write(crypto.createHash('sha256').update(JSON.stringify(cues)).digest('hex'));",
            str(OUTPUT / 'cues/02-lip-closures.json')], cwd=ROOT, text=True).strip()
        if cue_hash != video['cue_sha256']:
            raise ValueError('Video does not match the current cue timeline')
        if manifest['model']['prepared_sha256'] != expected['model_sha256']:
            raise ValueError('Model provenance is stale')
        for clip in manifest['clips']:
            if digest(OUTPUT / clip['file']) != clip['audio']['sha256']:
                raise ValueError('Audio changed after analysis')
        print(seal_pack(OUTPUT))
        return
    for name in ('audio', 'cues', 'licenses', 'proof'):
        (OUTPUT / name).mkdir(parents=True, exist_ok=True)
    for filename, *_ in REFERENCES:
        target = OUTPUT / 'audio' / filename
        if not target.is_file():
            sources = [ROOT / 'artifacts/face-voice-test-pack/audio' / filename,
                       Path('/home/user/Jali-Face-Voice-Test-Pack/audio') / filename]
            source = next((p for p in sources if p.is_file()), None)
            if source is None:
                raise FileNotFoundError(f'Place the existing stock reference at {target}')
            shutil.copy2(source, target)
    if args.reuse_cues:
        clips = []
        for filename, title, text, _ in REFERENCES:
            metrics = audio_metadata(OUTPUT / 'audio' / filename)
            relative = f'cues/{Path(filename).stem}.json'
            data = json.loads((OUTPUT / relative).read_text())
            expected_dialog = hashlib.sha256((text.replace('’', "'") + '\n').encode()).hexdigest()
            if data.get('provenance', {}).get('dialog_sha256') != expected_dialog:
                raise ValueError('Dialog changed; rerun without --reuse-cues')
            if data.get('provenance', {}).get('audio_sha256') != metrics['sha256']:
                raise ValueError('Cannot reuse cues from another recording; rerun without --reuse-cues')
            cues = validate_timeline(data, metrics['duration_seconds'])
            clips.append({'file': f'audio/{filename}', 'title': title, 'text': text,
                          'duration': metrics['duration_seconds'], 'cues': cues,
                          'audio': metrics, 'analysis_file': relative})
    else:
        clips = analyze(OUTPUT)
    if not (OUTPUT / 'model/mpfb-head.glb').is_file():
        prepare_model()
    else:
        original = CACHE / 'mpfb.glb'
        if not original.is_file():
            CACHE.mkdir(parents=True, exist_ok=True)
            original.write_bytes(github_file(f'repos/met4citizen/TalkingHead/contents/avatars/mpfb.glb?ref={SOURCE_COMMIT}'))
        if digest(original) != SOURCE_SHA:
            raise ValueError('Source model does not match the pinned source')
    source = (CACHE / 'mpfb.glb').read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
    if blob != 'cd2ebbe1fe8bcbf3d5b2dfbf1262a7f76814e68f':
        raise ValueError('Source model does not match the GitHub blob at the pinned commit')
    (OUTPUT / 'proof/source-model.json').write_text(json.dumps({
        'source_commit': SOURCE_COMMIT, 'github_blob_sha1': blob,
        'local_git_blob_sha1': blob, 'source_sha256': SOURCE_SHA,
        'bytes': len(source), 'matched_pinned_github_blob': True,
    }, indent=2) + '\n')
    licenses = OUTPUT / 'licenses'
    (licenses / 'model-source-README.md').write_bytes(github_file(f'repos/met4citizen/TalkingHead/contents/README.md?ref={SOURCE_COMMIT}'))
    # Preserve explicit per-asset CC0 statement rather than applying the software license to the model.
    text = (licenses / 'model-source-README.md').read_text()
    if 'mpfb.glb' not in text or 'licensed under [CC0]' not in text:
        raise ValueError('Expected explicit model license statement is absent')
    if not (licenses / 'CC0-1.0.txt').is_file():
        license_data = json.loads(subprocess.check_output(['gh', 'api', 'licenses/cc0-1.0'], timeout=30))
        (licenses / 'CC0-1.0.txt').write_text(license_data['body'])
    if not (licenses / 'Rhubarb-LICENSE.md').is_file():
        (licenses / 'Rhubarb-LICENSE.md').write_bytes(github_file('repos/DanielSWolf/rhubarb-lip-sync/contents/LICENSE.md?ref=v1.13.0'))
    shutil.copy2(ROOT / 'tools/node_modules/three/LICENSE', licenses / 'three-MIT.txt')
    shutil.copy2(ROOT / 'tools/node_modules/meshoptimizer/LICENSE.md', licenses / 'meshoptimizer-MIT.txt')
    shutil.copy2(ROOT / 'web/neural-head/index.html', OUTPUT / 'index.html')
    payload = 'window.JALI_HEAD_DATA=' + json.dumps({'clips': clips}, ensure_ascii=False)
    payload += ';\nwindow.JALI_HEAD_BASE64=' + json.dumps(base64.b64encode((OUTPUT / 'model/mpfb-head.glb').read_bytes()).decode()) + ';\n'
    (OUTPUT / 'demo-data.js').write_text(payload, encoding='utf-8')
    subprocess.run(['node', 'tools/bundle_head.cjs'], cwd=ROOT, check=True, timeout=60)
    # Compressed container validation cannot inspect meshopt's decoded attributes;
    # validate_head.cjs separately validates a fully decoded in-memory GLB.
    validation = subprocess.run(['node', 'tools/validate_character.cjs', str(OUTPUT / 'model/mpfb-head.glb')],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)
    issues = json.loads(validation.stdout)
    (OUTPUT / 'proof/compressed-model-validation.json').write_text(validation.stdout)
    if issues['numErrors']:
        raise ValueError('Invalid prepared character')
    subprocess.run(['node', 'tools/validate_head.cjs'], cwd=ROOT, check=True, timeout=60)
    decoded_issues = json.loads((OUTPUT / 'proof/decoded-model-validation.json').read_text())
    manifest = {
        'schema': 1, 'model': {
            'origin': 'TalkingHead MPFB/MakeHuman example avatar; head-and-shoulders presentation',
            'source_url': f'https://github.com/met4citizen/TalkingHead/blob/{SOURCE_COMMIT}/avatars/mpfb.glb',
            'license_evidence_url': f'https://github.com/met4citizen/TalkingHead/blob/{SOURCE_COMMIT}/README.md',
            'license': 'CC0 (explicitly stated for mpfb.glb by upstream)', 'source_sha256': SOURCE_SHA,
            'file': 'model/mpfb-head.glb', 'prepared_sha256': digest(OUTPUT / 'model/mpfb-head.glb'),
            'modifications': 'Textures resized to <=1024; quantized/Meshopt compressed; all 67 bones and 66 main-mesh facial targets retained',
            'runtime_budget': 'Viewer uploads 20 used face controls; unused source controls remain in the downloadable model',
            'decoded_validator_errors': decoded_issues['numErrors'], 'decoded_validator_warnings': decoded_issues['numWarnings'],
        },
        'clips': clips,
        'analysis': {'tool': 'Rhubarb 1.13.0 / PocketSphinx', 'method': 'dialog-guided estimated A-H/X mouth classes from actual WAVs',
                     'recognizer_package': ARCHIVE_URL, 'package_sha256': ARCHIVE_SHA, 'executable_sha256': BINARY_SHA,
                     'hand_verified': False, 'phoneme_forced_alignment': False, 'espeak_timings_reused': False},
        'renderer': 'Three.js r174 WebGL2, not the strict native Vulkan importer',
        'voice': 'Existing externally generated Arena stock voice, not local neural inference or a cloned identity',
        'video': {'file': 'rendered-lip-closures.mp4', 'clip': 'audio/02-lip-closures.wav', 'fps': 15,
                  'method': 'Offline browser capture with the same audio-derived cues; muxed original WAV into AAC'},
        'limitations': ['Approximate 9-class viseme retargeting, not a learned facial performance or certified AV sync.',
                        'Blink/head drift are procedural and expression styling is manual, not inferred emotion.',
                        'The native Vulkan importer does not support this richer asset yet.',
                        'Windows target-laptop performance has not been measured.'],
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    shutil.copy2(ROOT / 'docs/human-head-demo.txt', OUTPUT / 'README.txt')
    for scratch in ('provisional-validation.json', 'model-validation.json'):
        (OUTPUT / scratch).unlink(missing_ok=True)
    print('Demo prepared. Run smoke_neural_head.cjs to test/export, then --seal-only to package.')


if __name__ == '__main__':
    main()
