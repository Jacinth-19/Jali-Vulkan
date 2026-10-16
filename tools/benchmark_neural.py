"""Isolated, no-download, public-corpus benchmark. Reports never upload themselves."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from audit_native_rig import audit
from run_neural_ci import stop_server

ROOT=Path(__file__).resolve().parents[1]


def system_info():
    info={'platform':sys.platform,'os':platform.platform(),'python':platform.python_version(),'logical_cpu_hint':os.cpu_count()}
    if sys.platform=='win32':
        script="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); @{os=(Get-CimInstance Win32_OperatingSystem|Select-Object Caption,Version);cpu=(Get-CimInstance Win32_Processor|Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;graphics=(Get-CimInstance Win32_VideoController|Select-Object Name,DriverVersion)}|ConvertTo-Json -Depth 4 -Compress"
        try:
            info['windows']=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],encoding='utf-8',timeout=30))
        except (subprocess.SubprocessError,ValueError,OSError):
            info['inventory_status']='Windows inventory unavailable; no values invented'
    return info


def write_json(path,data):
    temp=path.with_name(path.name+f'.{os.getpid()}.part');temp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');temp.replace(path)


def run(repeats=2,browser=None,headless=False,conditions=''):
    if type(repeats) is not int or repeats not in (1,2,3) or len(conditions)>2000:
        raise ValueError('Repeats must be 1-3; conditions at most 2000 characters')
    browser=browser or ('chrome' if sys.platform=='win32' else 'sandbox')
    if browser not in ('chrome','msedge','sandbox') or (sys.platform=='win32' and browser=='sandbox'):
        raise ValueError('Select an installed Chrome/Edge browser on Windows')
    artifacts=ROOT/'artifacts';parent=artifacts/'benchmarks';parent.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=parent))
    latest=artifacts/'jali-benchmark-report.json';server=None
    result={'schema':'jali-neural-benchmark-v1','created_at':datetime.now(timezone.utc).isoformat(),
        'status':'running','run_id':directory.name,'system':system_info(),'conditions':conditions,
        'repeats_per_case':repeats,'dataset':'Fixed public synthetic articulation corpus; not private recordings',
        'privacy':'No automatic upload. OS/CPU/GPU/browser information and your conditions are included; inspect before sharing. Local logs/media stay in the run folder.',
        'm3':{'human_review_completed':False,'independently_verified_phoneme_alignment':False,'retarget_tuning_validated':False,'quality_score':None},
        'limits':['First request is not a reboot-cold benchmark. Every request uses a fresh speech process; later requests are not a persistent warm engine.',
                  'Render metrics count CPU-side renderer updates/submissions, not presented FPS, GPU execution, or physical AV latency.',
                  'Worker peak memory excludes server, browser/GPU and whole-system usage. Short clips do not establish thermal/long-utterance performance.',
                  'This report describes only the machine it was run on; hosted CI is not the user laptop.']}
    try:
        result['native_rig_audit']=audit(ROOT/'artifacts/neural-studio/model/mpfb-head.glb')
        with (directory/'server.log').open('w',encoding='utf-8') as log:
            start=time.monotonic();ready=directory/'ready.json'
            server=subprocess.Popen([sys.executable,'-u',str(ROOT/'tools/neural_studio_server.py'),'--bind','127.0.0.1','--port','0','--sessions',str(directory/'sessions'),'--ready-file',str(ready)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=(os.name!='nt'))
            while not ready.is_file():
                if server.poll() is not None:raise RuntimeError('server_startup_failed')
                if time.monotonic()-start>45:raise TimeoutError('server_readiness_timeout')
                time.sleep(.1)
            port=json.loads(ready.read_text(encoding='utf-8'))['port'];base=f'http://127.0.0.1:{port}'
            with urlopen(base+'/api/config',timeout=5):pass
            result['server_ready_seconds']=round(time.monotonic()-start,4)
            with (directory/'browser.log').open('w',encoding='utf-8') as browser_log:
                subprocess.run(['node','tools/benchmark_browser.cjs',base,str(directory),str(repeats),browser,str(headless).lower()],cwd=ROOT,stdout=browser_log,stderr=subprocess.STDOUT,check=True,timeout=repeats*900)
            result['browser']=json.loads((directory/'browser.json').read_text(encoding='utf-8'))
            expected=3*repeats;samples=result['browser']['samples']
            if len(samples)!=expected or not all(s['playback']['valid_sample'] for s in samples):raise ValueError('incomplete_samples')
            if result['browser']['external_request_count'] or result['browser']['browser_error_count']:raise ValueError('browser_contract_failed')
            result['status']='completed'
    except KeyboardInterrupt:
        result['status']='cancelled';result['error_type']='KeyboardInterrupt'
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,TimeoutError) as error:
        result['status']='failed';result['error_type']=type(error).__name__
        if (directory/'browser.json').is_file():result['partial_browser']=json.loads((directory/'browser.json').read_text(encoding='utf-8'))
        print('Benchmark did not complete. Inspect local run logs; do not treat partial samples as a passing result.',file=sys.stderr)
    finally:
        if server:
            try:stop_server(server)
            except (OSError,subprocess.SubprocessError):
                result['status']='failed';result['cleanup_error']=True
        write_json(directory/'report.json',result);write_json(latest,result)
    print(f'Report: {latest}\nLocal media, reference templates and logs: {directory}')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repeats',type=int,choices=(1,2,3),default=2)
    p.add_argument('--browser',choices=('chrome','msedge','sandbox'));p.add_argument('--headless',action='store_true')
    p.add_argument('--conditions',default='');a=p.parse_args()
    result=run(a.repeats,a.browser,a.headless,a.conditions)
    sys.exit(0 if result['status']=='completed' else 1)


if __name__=='__main__':main()
