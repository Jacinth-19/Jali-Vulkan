"""Fresh private workspace, explicit NON-SPEECH controls/storage/integration fixtures."""
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from upgrade_fixture_server import ROOT,fixture_pipeline
from neural_studio_server import StudioState,make_server
from studio_workspace import ControlBroker

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,default=ROOT/'artifacts/neural-studio');args=p.parse_args()
    assets=args.assets;rig=json.loads((assets/'rig.json').read_text())
    with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
        state=StudioState(Path(directory)/'sessions',rig,None,pipeline=fixture_pipeline);state.control=ControlBroker('explicit-public-ci-fixture-key-not-a-user-credential');server=make_server(assets,state,'127.0.0.1',0);server.RequestHandlerClass.log_message=lambda *_:None;thread=threading.Thread(target=server.serve_forever);thread.start()
        try:subprocess.run(['node','tools/smoke_workspace.cjs',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,check=True,timeout=240)
        finally:server.shutdown();server.server_close();thread.join();state.cancel_active();state.pool.shutdown(wait=True)
if __name__=='__main__':main()
