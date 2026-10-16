"""Frozen Windows entry point. No runtime installs, model downloads or gh access."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import webbrowser


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--speech-worker':
        del sys.argv[1]
        from local_neural_speech import main as speech_main
        speech_main();return
    p=argparse.ArgumentParser(description='Jali portable CPU neural face studio (local browser, no account)')
    p.add_argument('--port',type=int,default=8082);p.add_argument('--no-browser',action='store_true')
    p.add_argument('--sessions',type=Path);p.add_argument('--ready-file',type=Path)
    args=p.parse_args()
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
    try:studio_main()
    finally:ready.unlink(missing_ok=True)


if __name__=='__main__':main()
