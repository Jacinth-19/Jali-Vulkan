"""Frozen Windows entry point. No runtime installs, model downloads or gh access."""
import argparse
import os
from pathlib import Path
import sys
import json
import threading
import time
import webbrowser


def main():
    if getattr(sys,'frozen',False) and len(sys.argv)==1:
        from studio_launcher import main as launcher_main
        launcher_main();return
    if '--launcher-smoke' in sys.argv:
        from studio_launcher import main as launcher_main
        print(json.dumps(launcher_main(smoke=True)));return
    if '--doctor' in sys.argv:
        from studio_launcher import diagnostics
        print(json.dumps(diagnostics('--native' in sys.argv),indent=2));return
    if len(sys.argv)>1 and sys.argv[1]=='--speech-worker':
        del sys.argv[1]
        from local_neural_speech import main as speech_main
        speech_main();return
    p=argparse.ArgumentParser(description='Jali portable CPU neural face studio (local browser, no account)')
    p.add_argument('--serve',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--port',type=int,default=8082);p.add_argument('--no-browser',action='store_true')
    p.add_argument('--sessions',type=Path);p.add_argument('--ready-file',type=Path)
    p.add_argument('--native',action='store_true',help='Enable optional bundled Vulkan renderer, using the system Vulkan driver')
    p.add_argument('--verify-installation',action='store_true',help='Check bundled files and exit without starting a server or modifying sessions')
    p.add_argument('--diagnostics-file',type=Path,help='Write local JSON diagnostics here; contains no session text/audio or environment dump')
    args=p.parse_args()
    from package_integrity import verify_installation
    if args.diagnostics_file and args.diagnostics_file.resolve().is_relative_to(Path(sys.executable).resolve().parent):
        p.error('Write diagnostics outside the installation directory (for example under your TEMP folder)')
    if getattr(sys,'frozen',False) or args.verify_installation:
        report=verify_installation(Path(sys.executable).resolve().parent)
        if args.diagnostics_file:
            args.diagnostics_file.parent.mkdir(parents=True,exist_ok=True)
            args.diagnostics_file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if args.verify_installation or not report['verified']:
            print(json.dumps(report,indent=2),flush=True)
            if not report['verified']:raise SystemExit(2)
            return
    if args.native:
        from runtime_paths import ASSET_ROOT
        if not (ASSET_ROOT/'native/mpfb-native.glb').is_file():p.error('This personal package has no native renderer. Rebuild with --include-native after windows/setup-native.ps1, or omit --native to use WebGL.')
    data=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.jali')))/'JaliVulkan'
    data.mkdir(parents=True,exist_ok=True)
    sessions=args.sessions or data/'sessions'
    ready=args.ready_file or data/f'ready-{os.getpid()}.json';ready.unlink(missing_ok=True)
    if not args.no_browser:
        def open_when_ready():
            import json
            for _ in range(300):
                try:
                    port=json.loads(ready.read_text())['port'];webbrowser.open(f'http://127.0.0.1:{port}');return
                except (OSError,ValueError,KeyError):time.sleep(.1)
        threading.Thread(target=open_when_ready,daemon=True).start()
    print('Jali portable studio: localhost only. Ctrl+C stops it. No runtime downloads.',flush=True)
    print(f'Local session files: {sessions}. Previous run UUID folders are cleared at startup.',flush=True)
    from neural_studio_server import main as studio_main
    sys.argv=[sys.argv[0],'--bind','127.0.0.1','--port',str(args.port),'--sessions',str(sessions),'--ready-file',str(ready)]
    if args.native:sys.argv.extend(['--native-asset',str(ASSET_ROOT/'native/mpfb-native.glb')])
    try:studio_main()
    except Exception as e:
        report={'schema':'jali-startup-error-v1','error_type':type(e).__name__,'detail':str(e),'next_steps':'Check whether the port is in use; try --port 0. Run --verify-installation to check damage. Do not disable security or download replacement DLLs. No session contents/environment variables are collected.'}
        target=args.diagnostics_file or data/'last-startup-error.json'
        try:target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        except OSError:pass
        print(json.dumps(report,indent=2),file=sys.stderr,flush=True)
        raise SystemExit(1) from None
    finally:ready.unlink(missing_ok=True)


if __name__=='__main__':main()
