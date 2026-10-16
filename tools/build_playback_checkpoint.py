#!/usr/bin/env python3
"""Build a Windows-browser/offline playback checkpoint, NOT a Windows TTS port.

Only consumes the fixed public synthetic review corpus. No neural weights,
executables, private recordings, credentials or network-dependent runtime.
"""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from neural_session import validate_binding
from prepare_kokoro_cpu import MODEL_SHA, VOICE_SHA

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts/Jali-Laptop-Playback-Checkpoint'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_inputs(review, studio, corpus):
    report = json.loads((review / 'articulation.json').read_text())
    rig = json.loads((studio / 'rig.json').read_text())
    if digest(studio / 'viewer.js') != rig['viewer_sha256'] or digest(studio / 'model/mpfb-head.glb') != rig['model_sha256']:
        raise ValueError('Studio assets do not match rig identity')
    if [c['text'] for c in report['sessions']] != [c['text'] for c in corpus['cases']]:
        raise ValueError('Only the exact fixed public corpus may be packaged')
    for case, clip in zip(corpus['cases'], report['sessions']):
        prefix = review / 'sessions' / case['id']
        wav = prefix.with_name(prefix.name + '-audio.wav')
        cues = json.loads(prefix.with_name(prefix.name + '-cues.json').read_text())
        manifest = json.loads(prefix.with_name(prefix.name + '-manifest.json').read_text())
        text = prefix.with_name(prefix.name + '-requested-text.txt').read_text(encoding='utf-8')
        if manifest != clip or text != clip['text']:
            raise ValueError('Review manifest or requested text mismatch')
        if (clip['tts']['providers'] != ['CPUExecutionProvider'] or clip['tts']['model_sha256'] != MODEL_SHA
                or clip['tts']['voice_sha256'] != VOICE_SHA):
            raise ValueError('Unverified stock CPU speech provenance')
        expected_dialog = hashlib.sha256((text.replace('’', "'") + '\n').encode()).hexdigest()
        if cues['provenance'].get('dialog_sha256') != expected_dialog or clip['analysis'] != cues['provenance']:
            raise ValueError('Analyzed dialog/provenance mismatch')
        validate_binding(clip, wav, cues, rig)
    return report, rig


def build():
    review, studio = ROOT / 'artifacts/neural-review', ROOT / 'artifacts/neural-studio'
    corpus = json.loads((ROOT / 'tests/fixtures/neural-articulation.json').read_text())
    report, rig = validate_inputs(review, studio, corpus)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    paths = ['index.html','style.css','checkpoint.js','viewer.js','demo-data.js','README.txt']
    for name in ('index.html','style.css'):
        shutil.copy2(ROOT / 'web/playback-checkpoint' / name, OUTPUT / name)
    shutil.copy2(studio / 'viewer.js', OUTPUT / 'viewer.js')
    subprocess.run(['node','tools/bundle_head.cjs',str(OUTPUT / 'checkpoint.js'),
                    'web/playback-checkpoint/controller.js'],cwd=ROOT,check=True,timeout=60)
    clips=[]
    for case, clip in zip(corpus['cases'], report['sessions']):
        wav=review / 'sessions' / f"{case['id']}-audio.wav"
        clips.append({**clip,'title':case['id'].capitalize(),'review':case['review'],
                      'file':'data:audio/wav;base64,'+base64.b64encode(wav.read_bytes()).decode()})
    (OUTPUT / 'demo-data.js').write_text('window.JALI_HEAD_DATA='+json.dumps({'clips':clips,'live':False,'rig':rig})+';\nwindow.JALI_HEAD_BASE64='+json.dumps(base64.b64encode((studio / 'model/mpfb-head.glb').read_bytes()).decode())+';\n',encoding='utf-8')
    (OUTPUT / 'README.txt').write_text((ROOT / 'docs/windows-playback-checkpoint.txt').read_text(),encoding='utf-8')
    (OUTPUT / 'licenses').mkdir(exist_ok=True)
    for name in ('model-source-README.md','CC0-1.0.txt','three-MIT.txt','meshoptimizer-MIT.txt','Rhubarb-LICENSE.md'):
        shutil.copy2(studio / 'licenses' / name, OUTPUT / 'licenses' / name)
        paths.append('licenses/'+name)
    for name in ('Kokoro-Apache-2.0.txt','model-redistribution-README.md','kokoro-js-README.md'):
        shutil.copy2(ROOT / 'models/kokoro/licenses' / name, OUTPUT / 'licenses' / name)
        paths.append('licenses/'+name)
    manifest={'schema':'jali-playback-package-v1','scope':'Offline browser playback only; no Windows synthesis/backend or native Vulkan claim',
              'rig':rig,'corpus':[{'id':c['id'],'text':c['text'],'audio_sha256':c['audio']['sha256']} for c in clips],
              'files':{name:digest(OUTPUT / name) for name in paths}}
    (OUTPUT / 'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    paths.append('package-manifest.json')
    archive=OUTPUT.with_suffix('.zip')
    # Explicit allowlist: never include a leftover file, benchmark report or user note.
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for name in paths:
            bundle.write(OUTPUT / name,OUTPUT.name+'/'+name)
    print(f'Checkpoint: {archive} ({archive.stat().st_size:,} bytes; {len(paths)} allowlisted files)')
    return archive


if __name__ == '__main__':
    build()
