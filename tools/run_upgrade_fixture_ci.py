"""Browser regressions with explicitly declared non-speech transport fixtures."""
import json
import subprocess
import sys
import threading
from upgrade_fixture_server import ROOT,fixture_pipeline
from neural_studio_server import StudioState,make_server


def main():
    assets=ROOT/'artifacts/neural-studio';rig=json.loads((assets/'rig.json').read_text())
    state=StudioState(ROOT/'artifacts/upgrade-fixture-sessions',rig,None,pipeline=fixture_pipeline);server=make_server(assets,state,'127.0.0.1',0)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        for script in (['tools/smoke_creative_controls.cjs'] if '--creative-only' in sys.argv else ['tools/smoke_upgrade_controls.cjs','tools/smoke_creative_controls.cjs']):
            subprocess.run(['node',script,f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=180)
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-v','error','-i',str(ROOT/'artifacts/creative-proof/performance.webm'),'-map','0:v:0','-map','0:a:0','-f','null','-'],check=True,timeout=30)

    finally:server.shutdown();server.server_close();state.cancel_active();state.pool.shutdown(wait=True)


if __name__=='__main__':main()
