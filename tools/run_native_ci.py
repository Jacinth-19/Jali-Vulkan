"""Model-free native proof using ONLY verified public neural-corpus recordings."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
import argparse
from render_native_session import render
from neural_studio_server import StudioState,make_server
from native_studio import NativeStudio
from neural_session import validate_binding
from render_session import ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--software-vulkan',action='store_true');a=p.parse_args()
    compare=ROOT/'artifacts/native-compare';report=json.loads((compare/'source-articulation.json').read_text());asset=ROOT/'artifacts/native-head/mpfb-native.glb'
    manifest=compare/'sessions'/report['sessions'][0]['id']/'manifest.json';render(manifest,asset,ROOT/'artifacts/native-head-proof',a.software_vulkan)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=compare));threading.Thread(target=server.serve_forever,daemon=True).start()
    try:subprocess.run(['node','tools/compare_native_head.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=180)
    finally:server.shutdown();server.server_close()
    assets=ROOT/'artifacts/neural-studio';rig=json.loads((assets/'rig.json').read_text());state=StudioState(compare/'sessions',rig,None)
    try:
        for clip in report['sessions']:
            validate_binding(clip,compare/'sessions'/clip['id']/'audio.wav',json.loads((compare/'sessions'/clip['id']/'cues.json').read_text()),rig)
            state.jobs[clip['id']]={'id':clip['id'],'state':'ready','stage':'ready','clip':clip};state.ready.append(clip['id'])
        state.native=NativeStudio(asset,rig,a.software_vulkan);server=make_server(assets,state,'127.0.0.1',0);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:subprocess.run(['node','tools/smoke_native_studio.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=180)
        finally:server.shutdown();server.server_close()
    finally:
        state.cancel_active();state.pool.shutdown(wait=True)
        if state.native:state.native.close()


if __name__=='__main__':main()
