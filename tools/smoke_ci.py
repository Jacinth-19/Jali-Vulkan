#!/usr/bin/env python3
"""Run a bounded browser integration check with a disposable local preview server.

Uses the already-built native worker and inherited Vulkan ICD selection. Does not
install models, use private recordings, or leave a preview/worker process running.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024-65535')
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    url = f'http://127.0.0.1:{args.port}'
    with (artifacts / 'ci-preview.log').open('w') as log:
        server = subprocess.Popen(
            [sys.executable, '-u', str(ROOT / 'tools/preview_server.py'), '--port', str(args.port)],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    raise RuntimeError('Preview exited before readiness; see artifacts/ci-preview.log')
                try:
                    with urlopen(url + '/api/live/session', timeout=1) as response:
                        metadata = json.load(response)['session']
                    if not metadata or metadata['mode'] != 'live-mesh':
                        raise RuntimeError('Native session failed; see artifacts/ci-preview.log')
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Preview readiness timed out')
                    time.sleep(0.1)
            (artifacts / 'ci-session.json').write_text(json.dumps(metadata, indent=2) + '\n')
            print(f"Browser test device: {metadata['device']}; hardware={metadata['hardware_accelerated']}", flush=True)
            subprocess.run(['node', 'tools/smoke_preview.cjs', url], cwd=ROOT, check=True, timeout=120)
        finally:
            # The native renderer belongs to the same disposable process group.
            try:
                os.killpg(server.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait(timeout=5)


if __name__ == '__main__':
    main()
