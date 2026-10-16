"""Publish only actual native PNGs and small, public-synthetic proof metadata."""
import hashlib
import json
from pathlib import Path
import shutil
from render_session import ROOT
from render_native_session import render


def main():
    proof=ROOT/'artifacts/native-head-proof';review=json.loads((ROOT/'artifacts/neural-review/articulation.json').read_text());corpus=json.loads((ROOT/'tests/fixtures/neural-articulation.json').read_text())
    if [c['text'] for c in review['sessions']]!=[c['text'] for c in corpus['cases']]:raise ValueError('Only fixed public synthetic corpus')
    contacts=ROOT/'artifacts/native-contact-proof'
    render(ROOT/'artifacts/native-compare/sessions'/review['sessions'][1]['id']/'manifest.json',ROOT/'artifacts/native-head/mpfb-native.glb',contacts,software=True,video=False)
    out=ROOT/'docs/images';records=[]
    for directory,value,name in ((proof,'A','native-human-closure.png'),(contacts,'G','native-human-contact.png'),(proof,'F','native-human-rounding.png')):
        evidence=json.loads((directory/'session-evidence.json').read_text());frame=next(f for f in evidence['frames'] if f['estimated_class']==value)
        if not any(c['id']==evidence['session_id'] and c['audio']['sha256']==evidence['audio_sha256'] for c in review['sessions']):raise ValueError('Unexpected native session provenance')
        path=directory/frame['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=frame['sha256']:raise ValueError('Native frame hash differs')
        shutil.copy2(path,out/name);records.append({**frame,'file':name,'renderer':'native-vulkan-rich-v1','session_id':evidence['session_id'],'audio_sha256':evidence['audio_sha256'],'native_asset_sha256':evidence['native_asset_sha256'],'source_rig':evidence['source_rig'],'device':evidence['renderer']['device'],'hardware_accelerated':evidence['renderer']['hardware_accelerated'],'independent_phoneme_verification':False})
    source_files=['src/character.cpp','src/character_rich.inc','src/vulkan_renderer.cpp','src/vulkan_mesh.inc','src/rich.cpp','include/jali/character.hpp','shaders/skin.comp','shaders/mesh.vert','shaders/mesh.frag','tools/build_native_head.py','tools/prepare_native_head.cjs','tools/render_native_session.py']
    metadata={'schema':'jali-real-native-human-captures-v1','images':records,'source_files_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_files},
        'native_profile':json.loads((ROOT/'artifacts/native-head/profile.json').read_text()),'cpu_gpu':json.loads((proof/'gpu-reference.json').read_text()),'source_three_comparison':json.loads((proof/'source-comparison.json').read_text()),'native_browser':json.loads((proof/'native-browser.json').read_text()),
        'limits':'Real textured human Vulkan raster readback at exact neural-corpus cue times, not illustration, hardware/laptop FPS, independent articulation or physical AV acceptance.'}
    (out/'native-human-evidence.json').write_text(json.dumps(metadata,indent=2)+'\n')
    shutil.copy2(ROOT/'artifacts/neural-studio/proof/stream-check.json',ROOT/'docs/evidence/sentence-stream-local.json')
    summaries=[]
    for case in corpus['cases']:
        r=json.loads((ROOT/'artifacts/neural-review/phone-alignment'/case['id']/'alignment.json').read_text());summaries.append({'case':case['id'],'audio_sha256':r['audio_sha256'],'method':r['method'],'phones':len(r['phones']),'model_files':r['model_files'],'independent_of_rhubarb':False,'human_review_completed':False})
    (ROOT/'docs/evidence/phone-crosscheck-local.json').write_text(json.dumps(summaries,indent=2)+'\n')


if __name__=='__main__':main()
