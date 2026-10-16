"""Local desktop launcher/doctor. No downloads, elevation or silent renderer fallback."""
import argparse
import json
import os
from pathlib import Path
import platform
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from runtime_paths import ASSET_ROOT as ROOT,native_runtime


def data_directory():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.jali')))/'JaliVulkan'


def server_command(mode,preset,ready):
    if mode not in ('webgl','native') or preset not in ('low','balanced','high'):raise ValueError('Invalid launch selection')
    args=['--port','0','--ready-file',str(ready)]
    if getattr(sys,'frozen',False):
        args=['--serve','--no-browser',*args]
        if mode=='native':args.append('--native')
        return [sys.executable,*args]
    args=['--bind','127.0.0.1',*args]
    if mode=='native':args.extend(['--native-asset',str(ROOT/'artifacts/native-head/mpfb-native.glb')])
    return [sys.executable,str(ROOT/'tools/neural_studio_server.py'),*args]


def native_asset():return ROOT/('native/mpfb-native.glb' if getattr(sys,'frozen',False) else 'artifacts/native-head/mpfb-native.glb')


def diagnostics(probe_native=False):
    checks=[]
    def check(name,operation,repair):
        try:detail=operation();checks.append({'check':name,'ok':True,'detail':detail})
        except Exception as e:checks.append({'check':name,'ok':False,'detail':f'{type(e).__name__}: {e}','repair':repair})
    if getattr(sys,'frozen',False):
        def integrity():
            from package_integrity import verify_installation
            report=verify_installation(Path(sys.executable).resolve().parent)
            if not report['verified']:raise ValueError(json.dumps(report['issues']))
            return {'checked_files':report['checked_files'],'authenticity_verified':False}
        check('installation',integrity,'Extract the complete original personal ZIP into a NEW empty folder. Do not download individual DLLs.')
        if not checks[-1]['ok']:
            return {'schema':'jali-launcher-diagnostics-v1','checks':checks,'native_probe_refused':True,'limits':'Damaged installation: no bundled native binary executed. Restore your trusted full package.'}
    def speech():
        from local_neural_speech import verify_assets
        verify_assets(ROOT/'models/kokoro');return 'Pinned CPU model and voice hashes match'
    def analyzer():
        from analyze_neural_clips import verify_engine
        from neural_platform import analyzer_path
        verify_engine(analyzer_path());return 'Pinned platform analyzer hash matches'
    check('speech',speech,'Run windows/setup-neural.ps1 in the trusted developer checkout, or rebuild your personal bundle.')
    check('analyzer',analyzer,'Repeat explicit neural setup or restore the full bundle; no runtime downloads are attempted.')
    binary,_=native_runtime(ROOT)
    if probe_native:
        def native():
            if not binary.is_file() or not native_asset().is_file():raise FileNotFoundError('Native EXE/profile not present')
            from rich_worker import RichWorker
            with tempfile.TemporaryDirectory(prefix='jali-device-check-') as temp:
                worker=RichWorker(native_asset(),Path(temp),size=64)
                try:
                    rgba,_=worker.frame({})
                    if len(rgba)!=64*64*4:raise ValueError('Incomplete native readback')
                    return {**worker.metadata,'readback_bytes':len(rgba)}
                finally:worker.close()
        check('native-vulkan',native,'Use an official GPU driver with Vulkan support. Read the native engine log. WebGL remains an explicit alternative. Developer native setup: windows/setup-native.ps1. Do not disable security or fetch random DLLs.')
    return {'schema':'jali-launcher-diagnostics-v1','platform':platform.platform(),'python_runtime_bundled':bool(getattr(sys,'frozen',False)),'checks':checks,'native_available':binary.is_file() and native_asset().is_file(),'webgl':'Checked by the studio browser, not inferred from Python or native Vulkan','limits':'Local file/device checks; not a benchmark, human quality approval, code-signing or physical AV certification. Paths/errors may identify local folders; inspect before sharing.'}


def stop_owned(process):
    if process is None or process.poll() is not None:return
    if os.name=='nt':
        subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
    else:
        
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:return
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def main(smoke=False):
    import tkinter as tk
    from tkinter import ttk,messagebox
    root=tk.Tk();root.title('Jali Studio — local launcher');root.geometry('710x580')
    parent=ttk.Frame(root,padding=20);parent.pack(fill='both',expand=True)
    ttk.Label(parent,text='Jali Studio',font=('Segoe UI',22,'bold')).pack(anchor='w')
    ttk.Label(parent,text='Local CPU speech · choose your renderer · no runtime downloads').pack(anchor='w',pady=(0,16))
    mode=tk.StringVar(value='webgl');preset=tk.StringVar(value='balanced');status=tk.StringVar(value='Choose WebGL for the simplest start. Native Vulkan requires its bundled/developer backend.')
    row=ttk.Frame(parent);row.pack(fill='x')
    ttk.Label(row,text='Renderer').pack(side='left',padx=(0,12));ttk.Radiobutton(row,text='WebGL (browser)',variable=mode,value='webgl').pack(side='left')
    ttk.Radiobutton(row,text='Native Vulkan',variable=mode,value='native').pack(side='left',padx=12)
    row=ttk.Frame(parent);row.pack(fill='x',pady=12);ttk.Label(row,text='Performance starting point').pack(side='left',padx=(0,12));ttk.Combobox(row,textvariable=preset,values=['low','balanced','high'],state='readonly',width=14).pack(side='left')
    ttk.Label(parent,textvariable=status,wraplength=660).pack(fill='x',pady=12)
    output=tk.Text(parent,height=14,wrap='word');output.pack(fill='both',expand=True)
    events=queue.Queue();running={'process':None,'log':None,'starting':False,'closing':False,'epoch':0,'launch_thread':None}
    folder=data_directory();folder.mkdir(parents=True,exist_ok=True)
    buttons=ttk.Frame(parent);buttons.pack(fill='x',pady=(14,0))
    def worker(operation,epoch=None):
        try:events.put((epoch,'result',operation()))
        except Exception as e:
            if epoch is not None and epoch==running['epoch'] and running['starting']:stop_owned(running['process'])
            events.put((epoch,'error',str(e)))
    def doctor():
        if doctor_button['state']=='disabled':return
        doctor_button.configure(state='disabled')
        selected=mode.get();status.set('Checking files and selected device… no settings are changed.')
        def operation():
            report=diagnostics(selected=='native');path=folder/'launcher-diagnostics.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return ('diagnostics',report)
        threading.Thread(target=worker,args=(operation,)).start()
    def launch():
        if running['starting'] or running['process'] is not None:return
        selected=mode.get();choice=preset.get()
        if selected=='native' and not native_asset().is_file():messagebox.showerror('Native not prepared','Run windows/setup-native.ps1 or build with -IncludeNativeVulkan. Select WebGL to continue without native.');return
        running['epoch']+=1;epoch=running['epoch'];running['closing']=False
        running['starting']=True;status.set('Starting on a free loopback port…');start.configure(state='disabled')
        def operation():
            ready=folder/f'launcher-ready-{os.getpid()}-{epoch}.json';ready.unlink(missing_ok=True)
            log=(folder/'launcher-server.log').open('w',encoding='utf-8');running['log']=log
            process=subprocess.Popen(server_command(selected,choice,ready),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name!='nt')
            if epoch!=running['epoch']:stop_owned(process);log.close();raise RuntimeError('Launch cancelled')
            running['process']=process
            deadline=time.monotonic()+150
            while not ready.is_file():
                if epoch!=running['epoch']:stop_owned(process);log.close();raise RuntimeError('Launch cancelled')
                if process.poll() is not None:raise RuntimeError('Server could not start. '+(folder/'launcher-server.log').read_text(encoding='utf-8',errors='replace')[-3500:])
                if time.monotonic()>deadline:stop_owned(process);raise TimeoutError('Readiness timed out. Run diagnostics; see launcher-server.log.')
                time.sleep(.1)
            port=json.loads(ready.read_text())['port']
            if type(port) is not int or not 1<=port<=65535:raise ValueError('Invalid ready port')
            if epoch!=running['epoch']:stop_owned(process);raise RuntimeError('Launch cancelled')
            return ('launched',f'http://127.0.0.1:{port}/?preset={choice}&renderer={selected}')
        thread=threading.Thread(target=worker,args=(operation,epoch));running['launch_thread']=thread;thread.start()
    def stop():
        running['epoch']+=1;epoch=running['epoch'];running['closing']=True;status.set('Stopping only the process tree started by this launcher…')
        process=running['process']
        def operation():
            stop_owned(process)
            launch_thread=running['launch_thread']
            if launch_thread is not None:launch_thread.join()
            return ('stopped',None)
        threading.Thread(target=worker,args=(operation,epoch)).start()
    start=ttk.Button(buttons,text='Launch studio',command=launch);start.pack(side='left')
    doctor_button=ttk.Button(buttons,text='Run diagnostics',command=doctor);doctor_button.pack(side='left',padx=8)
    ttk.Button(buttons,text='Stop studio',command=stop).pack(side='left')
    def pump():
        while not events.empty():
            epoch,kind,value=events.get()
            if epoch is not None and epoch!=running['epoch']:continue
            if epoch is None:doctor_button.configure(state='normal')
            if kind=='error':
                running['starting']=False
                if running['process'] is None or running['process'].poll() is not None:
                    running['process']=None
                    if running['log']:running['log'].close();running['log']=None
                start.configure(state='normal');status.set('Could not start. Review the log/diagnostics; select WebGL explicitly if native is unavailable.');output.insert('end',value+'\n')
            else:
                name,content=value
                if name=='diagnostics':output.delete('1.0','end');output.insert('end',json.dumps(content,indent=2));status.set('Diagnostics saved locally: '+str(folder/'launcher-diagnostics.json'))
                if name=='launched':running['starting']=False;status.set('Running: '+content+' — close/Stop here to end this owned server.');
                    if not smoke:webbrowser.open(content)
                if name=='stopped':
                    running['process']=None;running['starting']=False;running['closing']=False
                    if running['log']:running['log'].close();running['log']=None
                    start.configure(state='normal');status.set('Stopped. Files remain in local app data; save wanted recordings before restarting.')
        process=running['process']
        if process is not None and process.poll() is not None and not running['starting']:
            running['process']=None;start.configure(state='normal');status.set('Server exited. Run diagnostics or inspect launcher-server.log.')
        root.after(100,pump)
    def close():
        running['epoch']+=1;running['closing']=True
        threading.Thread(target=stop_owned,args=(running['process'],)).start();root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    pump()
    if smoke:
        process=None
        try:
            root.update();launch();deadline=time.monotonic()+150
            while running['starting']:
                root.update()
                if time.monotonic()>deadline:raise TimeoutError('GUI launch smoke exceeded readiness deadline')
                time.sleep(.02)
            process=running['process']
            if process is None or process.poll() is not None:raise RuntimeError('GUI failed to launch: '+output.get('1.0','end'))
            stop();deadline=time.monotonic()+30
            while running['closing']:
                root.update()
                if time.monotonic()>deadline:raise TimeoutError('GUI Stop did not finish')
                time.sleep(.02)
            if process.poll() is None:raise RuntimeError('GUI left its owned server running')
            return {'schema':'jali-launcher-ui-smoke-v1','tk_window_created':True,'owned_server_started':True,'owned_server_stopped':True,'browser_suppressed_for_test':True,'renderer_choices':['webgl','native'],'preset_choices':['low','balanced','high']}
        finally:
            running['epoch']+=1;stop_owned(process or running['process']);root.destroy()
    root.mainloop()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--doctor',action='store_true');p.add_argument('--native',action='store_true');p.add_argument('--smoke',action='store_true');args=p.parse_args()
    if args.doctor:print(json.dumps(diagnostics(args.native),indent=2))
    elif args.smoke:print(json.dumps(main(smoke=True)))
    else:main()
