#!/usr/bin/env python3
"""Exercise the extracted/frozen Windows app from an unrelated working directory."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from run_neural_ci import stop_server

ROOT=Path(__file__).resolve().parents[1]


def main():
    app=ROOT/'artifacts/windows-portable/app/JaliStudio/JaliStudio.exe'
    proof=ROOT/'artifacts/windows-portable/proof';proof.mkdir(parents=True,exist_ok=True)
    ready=proof/'ready.json';ready.unlink(missing_ok=True)
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
    env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')+';'+os.environ['SystemRoot']
    with tempfile.TemporaryDirectory(prefix='jali-portable-cwd-') as cwd,(proof/'server.log').open('w',encoding='utf-8') as log:
        server=subprocess.Popen([str(app),'--port','0','--no-browser','--ready-file',str(ready),'--sessions',str(proof/'sessions')],cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while not ready.is_file():
                if server.poll() is not None:raise RuntimeError('Portable app exited; inspect server.log')
                if time.monotonic()>deadline:raise TimeoutError('Portable readiness timed out')
                time.sleep(.1)
            port=json.loads(ready.read_text())['port']
            subprocess.run([shutil.which('node'),str(ROOT/'tools/smoke_packaged.cjs'),f'http://127.0.0.1:{port}',str(proof/'browser.json')],cwd=ROOT,check=True,timeout=540)
        finally:stop_server(server)
    # Session fixtures are test inputs/outputs, not part of the redistributed ZIP.
    shutil.rmtree(proof/'sessions',ignore_errors=True)


if __name__=='__main__':main()
