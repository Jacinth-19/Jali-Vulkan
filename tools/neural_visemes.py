"""Native adapter for the shared JS retarget rules; parity is tested numerically."""
from bisect import bisect_right
import json
import math
import hashlib
import sys
from render_session import ROOT


def shared_shapes():
    # Generated from the authoritative JS table at build time, never at runtime.
    frozen=getattr(sys,'frozen',False)
    generated=ROOT/'artifacts/neural-studio/native-shapes.json'
    expected=json.loads((ROOT/'artifacts/neural-studio/rig.json').read_text())['retarget_sha256'] if frozen else hashlib.sha256((ROOT/'web/neural-head/visemes.mjs').read_bytes()).hexdigest()
    path=generated if frozen else ROOT/'web/neural-head/native-shapes.json'
    if not frozen and generated.is_file():
        candidate=json.loads(generated.read_text(encoding='utf-8'))
        if candidate.get('retarget_sha256')==expected:path=generated
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!='jali-native-shapes-v1' or data.get('retarget_sha256')!=expected:raise ValueError('Native shapes/source version mismatch; rebuild native-shapes.json with tools/build_native_shapes.cjs')
    shapes=data['shapes']
    if not isinstance(shapes,dict) or set(shapes)!=set('ABCDEFGHX'):raise ValueError('Invalid native cue classes')
    for shape in shapes.values():
        if not isinstance(shape,dict) or not isinstance(shape.get('weights'),dict) or len(shape['weights'])>80:raise ValueError('Invalid native shape weights')
        for name,value in shape['weights'].items():
            if not isinstance(name,str) or len(name)>128 or type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid native shape weight')
    return shapes


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
