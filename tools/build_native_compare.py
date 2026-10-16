#!/usr/bin/env python3
"""Create an offline source-Three reference page from the public neural corpus."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
from build_neural_head import prepare_model
from neural_session import validate_binding
from render_session import ROOT


def build(review):
    report=json.loads((review/'articulation.json').read_text());corpus=json.loads((ROOT/'tests/fixtures/neural-articulation.json').read_text())
    if [c['text'] for c in report['sessions']]!=[c['text'] for c in corpus['cases']]:raise ValueError('Only public corpus may be staged')
    output=ROOT/'artifacts/native-compare';output.mkdir(parents=True,exist_ok=True);(output/'audio').mkdir(exist_ok=True)
    clips=[]
    for case,clip in zip(corpus['cases'],report['sessions']):
        source=review/'sessions';directory=output/'sessions'/clip['id'];directory.mkdir(parents=True,exist_ok=True)
        for name in ('audio.wav','cues.json','manifest.json','requested-text.txt'):shutil.copy2(source/f"{case['id']}-{name}",directory/name)
        validate_binding(clip,directory/'audio.wav',json.loads((directory/'cues.json').read_text()),clip['rig'])
        shutil.copy2(directory/'audio.wav',output/'audio'/f"{case['id']}.wav");clips.append({**clip,'file':f"audio/{case['id']}.wav"})
    model=ROOT/'artifacts/neural-head-demo/model/mpfb-head.glb'
    if not model.is_file():prepare_model()
    html=(ROOT/'web/neural-head/index.html').read_text();html=html[:html.index('<section class="panel export">')]+'</main><script src="demo-data.js"></script><script src="viewer.js"></script></body></html>';(output/'index.html').write_text(html)
    subprocess.run(['node','tools/bundle_head.cjs',str(output/'viewer.js')],cwd=ROOT,check=True,timeout=60)
    data={'clips':clips,'rig':clips[0]['rig']}
    (output/'demo-data.js').write_text('window.JALI_HEAD_DATA='+json.dumps(data)+';\nwindow.JALI_HEAD_BASE64='+json.dumps(base64.b64encode(model.read_bytes()).decode())+';\n')
    (output/'source-articulation.json').write_text(json.dumps(report,indent=2)+'\n')
    return output,output/'sessions'/clips[0]['id']/'manifest.json'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,default=ROOT/'artifacts/neural-review');a=p.parse_args();print(build(a.review))
