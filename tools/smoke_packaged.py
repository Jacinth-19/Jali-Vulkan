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
        checks=[]
        def verify(expected):
            result=subprocess.run([str(app),'--verify-installation'],cwd=cwd,env=env,capture_output=True,text=True,timeout=120)
            if result.returncode!=(0 if expected else 2):raise RuntimeError(f'Unexpected frozen preflight exit: {result.returncode}: {result.stderr}')
            report=json.loads(result.stdout)
            if report['verified']!=expected:raise RuntimeError('Frozen integrity check did not detect damage')
            checks.append(report);return report
        verify(True)
        rig=app.parent/'_internal/artifacts/neural-studio/rig.json';original=rig.read_bytes()
        try:
            rig.write_bytes(original+b'\n');verify(False)
            result=subprocess.run([str(app),'--port','0','--no-browser','--ready-file',str(ready)],cwd=cwd,env=env,capture_output=True,text=True,timeout=120)
            if result.returncode!=2 or ready.exists():raise RuntimeError('Damaged package did not fail closed before serving')
        finally:rig.write_bytes(original)
        analyzer=next(app.parent.rglob('rhubarb.exe'));missing=proof/'missing-analyzer.exe';analyzer.rename(missing)
        try:verify(False)
        finally:missing.rename(analyzer)
        verify(True)
        (proof/'installation-checks.json').write_text(json.dumps({'schema':'jali-frozen-installation-proof-v1','positive_tampered_missing_restored':checks,'startup_failed_closed':True},indent=2)+'\n')
        native=['--native'] if (app.parent/'_internal/native/jali_rich.exe').is_file() else []
        server=subprocess.Popen([str(app),*native,'--port','0','--no-browser','--ready-file',str(ready),'--sessions',str(proof/'sessions')],cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+120
            while not ready.is_file():
                if server.poll() is not None:raise RuntimeError('Portable app exited: '+(proof/'server.log').read_text(encoding='utf-8',errors='replace')[-6000:])
                if time.monotonic()>deadline:raise TimeoutError('Portable readiness timed out')
                time.sleep(.1)
            port=json.loads(ready.read_text())['port']
            subprocess.run([shutil.which('node'),str(ROOT/'tools/smoke_packaged.cjs'),f'http://127.0.0.1:{port}',str(proof/'browser.json')],cwd=ROOT,check=True,timeout=540)
        finally:
            stop_server(server)
            native_log=Path(os.environ.get('LOCALAPPDATA',''))/'JaliVulkan/native-engine'/str(server.pid)/'engine.log'
            if native_log.is_file():shutil.copy2(native_log,proof/'native-engine.log')
        verify(True)
        (proof/'post-runtime-installation.json').write_text(json.dumps(checks[-1],indent=2)+'\n')
    # Session fixtures are test inputs/outputs, not part of the redistributed ZIP.
    shutil.rmtree(proof/'sessions',ignore_errors=True)


if __name__=='__main__':main()
