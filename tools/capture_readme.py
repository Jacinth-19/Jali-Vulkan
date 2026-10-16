#!/usr/bin/env python3
"""Publish small, actual WebGL review frames + a fresh native Vulkan capture.

Run the real neural browser review first (JALI_REVIEW=1 smoke_neural_studio.cjs).
No image synthesis, illustrative replacements, models or private WAVs are committed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image
from render_session import ROOT, runtime_environment


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(session_root, output, software=False):
    review=ROOT/'artifacts/neural-review'
    report=json.loads((review/'articulation.json').read_text())
    proof=json.loads((ROOT/'artifacts/neural-studio/proof/browser-check.json').read_text())
    rig=json.loads((ROOT/'artifacts/neural-studio/rig.json').read_text())
    corpus=json.loads((ROOT/'tests/fixtures/neural-articulation.json').read_text())
    if rig['viewer_sha256']!=sha(ROOT/'artifacts/neural-studio/viewer.js') or rig['model_sha256']!=sha(ROOT/'artifacts/neural-studio/model/mpfb-head.glb'):
        raise ValueError('Installed viewer or model does not match its rig identity')
    if not proof['passed'] or proof['errors'] or proof['external_requests']:
        raise ValueError('A successful real browser review is required')
    if [c['text'] for c in report['sessions']] != [c['text'] for c in corpus['cases']]:
        raise ValueError('Only the fixed public synthetic corpus may be published')
    if [c['id'] for c in proof['sessions']] != [c['id'] for c in report['sessions']]:
        raise ValueError('Review and browser proof sessions differ')
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    for case,value,name in [('closures','A','webgl-closure.png'),('contacts','G','webgl-contact.png'),('vowels','F','webgl-rounding.png')]:
        frame=next(f for f in report['frames'] if f['case']==case and f['value']==value)
        clip=report['sessions'][next(i for i,c in enumerate(corpus['cases']) if c['id']==case)]
        wav=session_root/clip['id']/'audio.wav'
        if clip['rig']!=rig or sha(wav)!=clip['audio']['sha256'] or clip['analysis']['audio_sha256']!=sha(wav):
            raise ValueError('Stale rig or mismatched actual WAV')
        source=review/frame['file']
        with Image.open(source) as im:
            if im.size!=(512,512) or im.format!='PNG':raise ValueError('Unexpected render dimensions/format')
            im.verify()
        shutil.copy2(source,output/name)
        records.append({'file':name,'sha256':sha(output/name),'renderer':'Three.js / WebGL',
            'source_frame':frame['file'],'audio_time_seconds':frame['time'],'estimated_class':value,'weights':frame['weights'],
            'text':clip['text'],'audio_sha256':clip['audio']['sha256'],'rig':rig,
            'style':'neutral; procedural motion disabled','independent_phoneme_verification':False})
    # This is the native ORIGINAL android fixture, not a Vulkan render of MPFB.
    binary=ROOT/'build-live/jali_live';asset=ROOT/'build-live/assets/android-67.glb'
    scratch=ROOT/'artifacts/readme-native';scratch.mkdir(parents=True,exist_ok=True)
    text='Hello from Jali. Please bring my blue paper bag.'
    process=subprocess.Popen([str(binary),'--asset',str(asset),'--output',str(scratch),'--text',text,'--size','512'],
        env=runtime_environment(software),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        stdout,stderr=process.communicate(input=b'0.65\nquit\n',timeout=45)
        header,pixels=stdout.split(b'\n',1);metadata=json.loads(header)
        if process.returncode or len(pixels)!=512*512*4:raise RuntimeError(f'Native capture failed: {stderr.decode(errors="replace")}')
    finally:
        if process.poll() is None:process.kill();process.communicate(timeout=5)
    if metadata['bones']!=67:raise ValueError('Expected actual 67-joint native fixture')
    target=output/'native-vulkan.png'
    Image.frombytes('RGBA',(512,512),pixels).convert('RGB').save(target,optimize=True)
    records.append({'file':target.name,'sha256':sha(target),'renderer':'native Vulkan compute skinning + indexed rasterization',
        'model':'original Jali android, 67-joint test fixture (NOT detailed MPFB head)','model_sha256':sha(asset),
        'audio_time_seconds':.65,'audio_sha256':sha(scratch/'session.wav'),'metadata':metadata})
    sources=['tools/capture_readme.py','tools/smoke_neural_studio.cjs','web/neural-head/viewer.js',
        'web/neural-head/visemes.mjs','web/neural-head/performance.mjs','src/character.cpp','src/vulkan_mesh.inc',
        'include/jali/character.hpp','shaders/skin.comp','shaders/mesh.vert','shaders/mesh.frag','tools/make_character.py','tests/backend_tests.cpp']
    evidence={'schema':'jali-readme-renders-v1','created_utc':datetime.now(timezone.utc).isoformat(),
        'method':'Actual deterministic WebGL canvas exports and a fresh native Vulkan RGBA readback; no generated/mock images',
        'source_files_sha256':{p:sha(ROOT/p) for p in sources},'images':records,
        'limits':'Pose/render evidence only, not independent articulation quality, physical AV sync or target-laptop performance acceptance. Detailed MPFB remains WebGL-only.'}
    (output/'render-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'images':[r['file'] for r in records],'native_device':metadata['device'],'hardware':metadata['hardware_accelerated']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session-root',type=Path,default=ROOT/'artifacts/neural-studio-sessions')
    p.add_argument('--output',type=Path,default=ROOT/'docs/images')
    p.add_argument('--software-vulkan',action='store_true')
    a=p.parse_args();capture(a.session_root.resolve(),a.output.resolve(),a.software_vulkan)
