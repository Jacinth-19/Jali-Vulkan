"""Native adapter for the shared JS retarget rules; parity is tested numerically."""
from bisect import bisect_right
import json
import math
import subprocess
from render_session import ROOT


def shared_shapes():
    return json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {SHAPES} from './web/neural-head/visemes.mjs';console.log(JSON.stringify(SHAPES))"],cwd=ROOT,text=True,timeout=15))


def sample(clip,time,shapes,offset=0,enabled=True):
    if isinstance(time,bool) or isinstance(offset,bool) or not isinstance(time,(int,float)) or not math.isfinite(time) or not math.isfinite(offset):raise ValueError('Invalid audio clock')
    cues=clip['cues']
    if not enabled or time<0 or time>=clip['duration'] or not cues:return {}
    time+=offset
    if time<cues[0]['start'] or time>=cues[-1]['end']:return {}
    index=max(0,bisect_right([c['start'] for c in cues],time)-1);cue=cues[index]
    weights=dict(shapes[cue['value']]['weights'])
    if index+1<len(cues):
        other=shapes[cues[index+1]['value']]['weights'];transition=min(.035,(cue['end']-cue['start'])*.35)
        alpha=max(0,min(1,(time-(cue['end']-transition))/transition))
        if alpha>0:weights={key:weights.get(key,0)*(1-alpha)+other.get(key,0)*alpha for key in weights.keys()|other.keys()}
    return weights
