#!/usr/bin/env python3
"""Explicitly prepare the M2 studio. Runtime requests never download models.

Requires Node tools, Pillow and the already prepared local Kokoro assets.
Uses an explicitly selected, checksum-pinned x64 Linux or Windows analyzer.
"""
import base64
import json
from pathlib import Path
import shutil
import subprocess

from analyze_neural_clips import ensure_engine, digest
from build_neural_head import prepare_model, github_file, SOURCE_COMMIT, SOURCE_SHA
from local_neural_speech import verify_assets
from prepare_kokoro_cpu import ASSETS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts/neural-studio'


def build(*,prepare_speech=True):
    if prepare_speech:
        verify_assets(ASSETS)
        ensure_engine()
    model = ROOT / 'artifacts/neural-head-demo/model/mpfb-head.glb'
    if not model.is_file():
        prepare_model()
    elif not (ROOT / '.cache/lipsync/mpfb.glb').is_file() or digest(ROOT / '.cache/lipsync/mpfb.glb') != SOURCE_SHA:
        prepare_model()
    (OUTPUT / 'licenses').mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'model').mkdir(exist_ok=True)
    for name in ('index.html','style.css'):
        shutil.copy2(ROOT / 'web/neural-studio' / name, OUTPUT / name)
    subprocess.run(['node','tools/bundle_head.cjs',str(OUTPUT/'controller.js'),'web/neural-studio/controller.js'],cwd=ROOT,check=True,timeout=60)
    shutil.copy2(model, OUTPUT / 'model/mpfb-head.glb')
    subprocess.run(['node', 'tools/bundle_head.cjs', str(OUTPUT / 'viewer.js')], cwd=ROOT, check=True, timeout=60)
    subprocess.run(['node', 'tools/validate_head.cjs', str(model), str(OUTPUT / 'proof/decoded-model-validation.json')], cwd=ROOT, check=True, timeout=60)
    rig = {'profile':'mpfb-rhubarb-9-v1', 'source_commit': SOURCE_COMMIT,
           'model_sha256':digest(model), 'retarget_sha256':digest(ROOT / 'web/neural-head/visemes.mjs'),
           'viewer_sha256':digest(OUTPUT / 'viewer.js')}
    subprocess.run(['node','tools/build_native_shapes.cjs',str(OUTPUT/'native-shapes.json')],cwd=ROOT,check=True,timeout=15)
    (OUTPUT / 'rig.json').write_text(json.dumps(rig, indent=2) + '\n')
    data = {'clips': [], 'live': True, 'rig': rig}
    (OUTPUT / 'demo-data.js').write_text('window.JALI_HEAD_DATA='+json.dumps(data)+';\nwindow.JALI_HEAD_BASE64='+json.dumps(base64.b64encode(model.read_bytes()).decode())+';\n')
    readme = github_file(f'repos/met4citizen/TalkingHead/contents/README.md?ref={SOURCE_COMMIT}')
    if b'licensed under [CC0]' not in readme or b'mpfb.glb' not in readme:
        raise ValueError('Explicit model license statement is missing')
    (OUTPUT / 'licenses/model-source-README.md').write_bytes(readme)
    for package, source, target in (
        ('webm-muxer', 'LICENSE', 'webm-muxer-MIT.txt'), ('three', 'LICENSE', 'three-MIT.txt'), ('meshoptimizer', 'LICENSE.md', 'meshoptimizer-MIT.txt')
    ):
        shutil.copy2(ROOT / 'tools/node_modules' / package / source, OUTPUT / 'licenses' / target)
    (OUTPUT / 'licenses/CC0-1.0.txt').write_text(subprocess.check_output(['gh','api','licenses/cc0-1.0','--jq','.body'], text=True, encoding='utf-8'))
    (OUTPUT / 'licenses/Rhubarb-LICENSE.md').write_bytes(github_file('repos/DanielSWolf/rhubarb-lip-sync/contents/LICENSE.md?ref=v1.13.0'))
    print(f'Studio prepared: {OUTPUT}. Run .venv/bin/python tools/neural_studio_server.py')


if __name__ == '__main__':
    build()
