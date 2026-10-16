#!/usr/bin/env python3
"""Disposable hosted CPU/browser check. Public synthetic corpus only; no uploads here."""
import html
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from neural_session import SESSION_ID

ROOT = Path(__file__).resolve().parents[1]


def collect_review():
    review = ROOT / 'artifacts/neural-review'
    report = json.loads((review / 'articulation.json').read_text())
    corpus = json.loads((ROOT / 'tests/fixtures/neural-articulation.json').read_text())
    if [c['text'] for c in report['sessions']] != [c['text'] for c in corpus['cases']]:
        raise ValueError('Refusing to collect anything except the fixed public synthetic corpus')
    (review / 'sessions').mkdir(exist_ok=True)
    sections = []
    for case, clip in zip(corpus['cases'], report['sessions']):
        if not SESSION_ID.fullmatch(clip['id']):
            raise ValueError('Invalid review session ID')
        for name in ('audio.wav', 'cues.json', 'requested-text.txt', 'manifest.json'):
            source = ROOT / 'artifacts/neural-studio-sessions' / clip['id'] / name
            shutil.copy2(source, review / 'sessions' / f"{case['id']}-{name}")
        frames = [frame for frame in report['frames'] if frame['case'] == case['id']]
        pictures = ''.join(f'<figure><img src="{html.escape(f["file"],quote=True)}" alt="Estimated shape {f["value"]}"><figcaption>{f["value"]} at {f["time"]:.3f} s — estimated class, not a verified phoneme</figcaption></figure>' for f in frames)
        sections.append(f'<section><h2>{html.escape(case["id"])}</h2><p>{html.escape(case["text"])}</p><audio controls src="sessions/{case["id"]}-audio.wav"></audio><p>Review: {html.escape(case["review"])}</p><div>{pictures}</div></section>')
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jali M3 articulation review</title><style>body{font:16px/1.6 system-ui;background:#101a1d;color:#efece3;max-width:1250px;margin:auto;padding:25px}p{max-width:900px}section{border-top:1px solid #465959;padding:20px 0}section>div{display:flex;flex-wrap:wrap}figure{margin:10px;max-width:240px}img{width:100%}figcaption{font-size:12px;color:#acc8bb}audio{width:min(100%,500px)}</style><h1>M3 articulation review</h1><p>Actual local neural recordings and estimated mouth poses. Automatic checks verify retarget contracts, NOT phoneme correctness, visible lip seal, naturalness or physical AV synchronization. Human review is still pending. Open this page after extracting the artifact completely.</p>' + ''.join(sections) + '</html>'
    (review / 'index.html').write_text(document, encoding='utf-8')
    proof = ROOT / 'artifacts/neural-studio/proof'
    for name in ('browser-check.json','decoded-model-validation.json','new-text-performance.mp4','poster.jpg','desktop.png','mobile.png','video-export.json'):
        if (proof / name).is_file():
            shutil.copy2(proof / name, review / name)
    shutil.copytree(ROOT / 'artifacts/neural-studio/licenses', review / 'licenses', dirs_exist_ok=True)


def main():
    port = 8082
    # Do not start a disposable server over somebody's running development preview.
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', port))
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    with (artifacts / 'neural-ci-server.log').open('w') as log:
        server = subprocess.Popen([sys.executable, '-u', 'tools/neural_studio_server.py', '--port', str(port)],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 45
            while True:
                if server.poll() is not None:
                    raise RuntimeError('Neural server exited before readiness')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/config', timeout=1):
                        break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Neural server readiness timed out')
                    time.sleep(.1)
            env = {**os.environ, 'JALI_REVIEW': '1', 'EXPORT_VIDEO': '1'}
            subprocess.run(['node','tools/smoke_neural_studio.cjs', f'http://127.0.0.1:{port}'],
                           cwd=ROOT, env=env, check=True, timeout=720)
            collect_review()
        finally:
            try:
                os.killpg(server.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
