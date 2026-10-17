#!/usr/bin/env python3
"""Developer-only, explicit replay of the TWO pinned public comparison recordings.

Not an archive migration API. No new synthesis/alignment/benchmark is claimed.
Runtime rig checks remain unchanged. Requires the original verified session WAVs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import uuid
from neural_session import validate_binding
from neural_studio_server import StudioState,make_server

ROOT=Path(__file__).resolve().parents[1]


def require_appearance_only_change(old,new):
    if not isinstance(old,dict) or not isinstance(new,dict) or set(old)!=set(new):
        raise ValueError('Comparison rigs must have identical fields')
    if {k:v for k,v in old.items() if k!='viewer_sha256'}!={k:v for k,v in new.items() if k!='viewer_sha256'}:
        raise ValueError('Only viewer identity may change in this explicit appearance comparison')
    if old.get('viewer_sha256')==new.get('viewer_sha256'):
        raise ValueError('Expected an explicitly changed viewer')


def prepare_replay(source,assets,sessions,character):
    source,assets,sessions=map(Path,(source,assets,sessions))
    expected=json.loads((ROOT/'docs/evidence/makehuman-skin-preview.json').read_text())['previews'][character]
    clip=json.loads((source/'manifest.json').read_text());cues=json.loads((source/'cues.json').read_text())
    validate_binding(clip,source/'audio.wav',cues,clip['rig'])
    if clip['audio']['sha256']!=expected['audio_sha256'] or clip['text_sha256']!=expected['text_sha256'] or clip['rig']!=expected['rig'] or clip.get('speaker')!=expected['speaker']:
        raise ValueError('Only the pinned public MakeHuman preview session is allowed')
    rig=json.loads((assets/'rig.json').read_text());require_appearance_only_change(clip['rig'],rig)
    for name,key in [('viewer.js','viewer_sha256'),('model/mpfb-head.glb','model_sha256')]:
        if hashlib.sha256((assets/name).read_bytes()).hexdigest()!=rig[key]:raise ValueError('Prepared comparison asset identity mismatch')
    ident=uuid.uuid4().hex;dest=sessions/ident;dest.mkdir(parents=True,exist_ok=False)
    try:
        for name in ['audio.wav','cues.json','requested-text.txt']:shutil.copy2(source/name,dest/name)
        updated=copy.deepcopy(clip);updated.update(id=ident,file=f'/sessions/{ident}/audio.wav',rig=rig,title='Explicit same-WAV appearance comparison')
        updated['comparison_replay']={'source_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),'source_rig':clip['rig'],'source_session_id':clip['id'],'new_synthesis':False,'new_alignment':False,'metrics_scope':'Original recording metrics, not a new performance benchmark','scope':'Explicit developer replay of pinned public fixture; only viewer identity changed. No runtime/archive identity checks weakened.'}
        validate_binding(updated,dest/'audio.wav',cues,rig)
        (dest/'manifest.json').write_text(json.dumps(updated,indent=2)+'\n')
        return ident,rig
    except BaseException:
        shutil.rmtree(dest);raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-session',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--sessions',type=Path,required=True);p.add_argument('--character',choices=['female','male'],required=True);p.add_argument('--port',type=int,required=True)
    a=p.parse_args();ident,rig=prepare_replay(a.source_session,a.assets,a.sessions,a.character)
    def reject(*_):raise ValueError('Explicit comparison-only server: use its prepared replay; no synthesis')
    state=StudioState(a.sessions,rig,None,pipeline=reject);state.ready.append(ident)
    server=make_server(a.assets,state,'0.0.0.0',a.port)
    print(json.dumps({'comparison_session':ident,'character':a.character,'port':a.port,'new_synthesis':False}),flush=True)
    try:server.serve_forever()
    finally:server.server_close();state.cancel_active();state.pool.shutdown(wait=True)


if __name__=='__main__':main()
