"""Development/test fixture server: real rig, explicitly NON-SPEECH PCM/cues.

Never used by production synthesis or represented as an articulation quality test.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import wave
from neural_studio_server import StudioState,make_server
from neural_session import text_hash
from analyze_neural_clips import audio_metadata
ROOT=Path(__file__).resolve().parents[1]


def fixture_pipeline(ident,text,directory,rig,rhubarb,stage):
    stage('synthesizing');directory.mkdir();duration=3;rate=24000
    with wave.open(str(directory/'audio.wav'),'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b''.join(struct.pack('<h',int(math.sin(i*.025)*500)) for i in range(duration*rate)))
    audio=audio_metadata(directory/'audio.wav');analysis={'audio_sha256':audio['sha256'],'method':'Explicit non-speech PCM/cue transport fixture, NOT inference/alignment or quality proof'}
    cues=[{'start':0,'end':.8,'value':'A'},{'start':.8,'end':1.5,'value':'G'},{'start':1.5,'end':2.3,'value':'H'},{'start':2.3,'end':3,'value':'X'}]
    clip={'id':ident,'text':text,'text_sha256':text_hash(text),'file':f'/sessions/{ident}/audio.wav','duration':duration,'audio':audio,'cues':cues,'rig':rig,'analysis':analysis,'tts':{'engine_load_seconds':0,'process_peak_rss_mib':None},'generation_seconds':0,'analysis_seconds':0,'total_seconds':0}
    (directory/'cues.json').write_text(json.dumps({'metadata':{'duration':duration},'mouthCues':cues,'provenance':analysis}));return clip


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8083);args=p.parse_args()
    assets=ROOT/'artifacts/neural-studio';rig=json.loads((assets/'rig.json').read_text());state=StudioState(ROOT/'artifacts/upgrade-fixture-sessions',rig,None,pipeline=fixture_pipeline)
    server=make_server(assets,state,'0.0.0.0',args.port)
    print('NON-SPEECH fixture server; no synthesis/quality claim',flush=True)
    try:server.serve_forever()
    finally:server.server_close();state.cancel_active();state.pool.shutdown(wait=True)
