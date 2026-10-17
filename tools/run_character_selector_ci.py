"""Browser check with explicit NON-SPEECH transport fixtures, not lip-sync proof."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from character_studio_server import make_character_server, close_character_server
from upgrade_fixture_server import fixture_pipeline
from runtime_paths import ASSET_ROOT as ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--female',type=Path,required=True);p.add_argument('--male',type=Path,required=True);p.add_argument('--authored-appearance',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='jali-selector-') as directory:
        server=make_character_server(a.female,a.male,Path(directory),None,pipeline=fixture_pipeline)
        server.RequestHandlerClass.log_message=lambda *_:None
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            subprocess.run(['node','tools/smoke_character_selector.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=300)
            subprocess.run(['node','tools/smoke_renderer_lease.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=300)
            if a.authored_appearance:subprocess.run(['node','tools/inspect_authored_appearance.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=300)
            if a.authored_appearance:subprocess.run(['node','tools/test_contact_browser.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=300)
            if a.authored_appearance:subprocess.run(['node','tools/inspect_eye_clearance.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=300)
            out=ROOT/'artifacts/character-selector-proof/browser.json';r=json.loads(out.read_text());r['speech_source']='Explicit NON-SPEECH fixture; not inference or alignment acceptance';out.write_text(json.dumps(r,indent=2)+'\n')
        finally:
            server.shutdown();thread.join();close_character_server(server)


if __name__=='__main__':main()
