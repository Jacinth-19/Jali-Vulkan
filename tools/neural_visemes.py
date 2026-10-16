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


def articulation(profile=None):
    presets={'baseline':dict(closure=1,contact=1,tongue=1,jaw=1,rounding=1,transition=35,smooth=False),'clear':dict(closure=1.05,contact=1.1,tongue=1.12,jaw=1,rounding=1.05,transition=35,smooth=True),'soft':dict(closure=1,contact=1,tongue=1,jaw=.9,rounding=.95,transition=50,smooth=True)}
    limits={'closure':(.75,1.15),'contact':(.7,1.2),'tongue':(.5,1.5),'jaw':(.7,1.2),'rounding':(.7,1.2),'transition':(0,70)}
    if profile is None:profile='baseline'
    if isinstance(profile,str):
        if profile not in presets:raise ValueError('Unknown articulation profile')
        profile=presets[profile]
    if not isinstance(profile,dict) or set(profile)-set(presets['baseline']):raise ValueError('Invalid articulation settings')
    p={**presets['baseline'],**profile}
    for k,(lo,hi) in limits.items():
        if type(p[k]) not in (int,float) or not math.isfinite(p[k]) or not lo<=p[k]<=hi:raise ValueError('Invalid articulation '+k)
    if type(p['smooth']) is not bool:raise ValueError('Invalid smoothing')
    return p


def calibrated(weights,p):
    return {k:min(1,max(0,v*(p['closure'] if k=='viseme_PP' else p['contact'] if k=='viseme_FF' else p['tongue'] if k in ('viseme_nn','viseme_DD') else p['jaw'] if k=='viseme_aa' else p['rounding'] if k in ('viseme_U','viseme_O') else 1))) for k,v in weights.items()}


def sample(clip,time,shapes,offset=0,enabled=True,profile=None):
    if isinstance(time,bool) or isinstance(offset,bool) or not isinstance(time,(int,float)) or not math.isfinite(time) or not math.isfinite(offset):raise ValueError('Invalid audio clock')
    cues=clip['cues']
    if not enabled or time<0 or time>=clip['duration'] or not cues:return {}
    time+=offset
    if time<cues[0]['start'] or time>=cues[-1]['end']:return {}
    index=max(0,bisect_right([c['start'] for c in cues],time)-1);cue=cues[index]
    p=articulation(profile);weights=calibrated(shapes[cue['value']]['weights'],p)
    if index+1<len(cues):
        other=calibrated(shapes[cues[index+1]['value']]['weights'],p);transition=min(p['transition']/1000,(cue['end']-cue['start'])*.35)
        alpha=max(0,min(1,(time-(cue['end']-transition))/transition)) if transition else 0
        if p['smooth']:alpha=alpha*alpha*(3-2*alpha)
        if alpha>0:weights={key:weights.get(key,0)*(1-alpha)+other.get(key,0)*alpha for key in weights.keys()|other.keys()}
    return weights
