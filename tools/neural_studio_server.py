#!/usr/bin/env python3
"""Development-only local neural speech + WebGL face studio; no upload/cloud API.

Run after build_neural_studio.py. One bounded job at a time; six ready sessions
retained in this run. The request token/origin policy prevents browser CSRF, NOT
remote-user authentication. Do not expose as a public service or enter secrets.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import shutil
import threading
from urllib.parse import urlparse
import uuid

from analyze_neural_clips import BINARY_SHA, digest
from local_neural_speech import validate_request, verify_assets
from neural_session import build_session, SESSION_ID, MEDIA, ROOT
from preview_server import Handler as FileHandler
from http.server import ThreadingHTTPServer

STATIC = {'/': 'index.html', '/style.css': 'style.css', '/controller.js': 'controller.js',
          '/viewer.js': 'viewer.js', '/demo-data.js': 'demo-data.js',
          '/rig.json': 'rig.json', '/licenses/model-source-README.md': 'licenses/model-source-README.md'}


class StudioState:
    def __init__(self, directory, rig, rhubarb, pipeline=build_session):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.rig, self.rhubarb, self.pipeline = rig, rhubarb, pipeline
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}
        self.ready = []
        self.failed = []
        self.busy = False
        self.token = secrets.token_hex(32)

    def start(self, text):
        validate_request(text)
        with self.lock:
            if self.busy:
                return None
            self.busy = True
            ident = uuid.uuid4().hex
            self.jobs[ident] = {'state': 'running', 'stage': 'queued', 'id': ident}
        self.pool.submit(self.perform, ident, text)
        return ident

    def perform(self, ident, text):
        def stage(value):
            with self.lock:
                self.jobs[ident] = {'state': 'running', 'stage': value, 'id': ident}
        try:
            clip = self.pipeline(ident, text, self.root / ident, self.rig, self.rhubarb, stage)
            with self.lock:
                self.jobs[ident] = {'state': 'ready', 'stage': 'ready', 'id': ident, 'clip': clip}
                self.ready.append(ident)
                while len(self.ready) > 6:
                    old = self.ready.pop(0)
                    self.jobs.pop(old, None)
                    shutil.rmtree(self.root / old, ignore_errors=True)
        except Exception as error:
            shutil.rmtree(self.root / ident, ignore_errors=True)
            with self.lock:
                self.jobs[ident] = {'state': 'error', 'stage': 'error', 'id': ident,
                                    'error': f'Local generation/analysis failed ({type(error).__name__}). No substitute audio or cues were used. Try a shorter English sentence.'}
                self.failed.append(ident)
                for old in self.failed[:-6]:
                    self.jobs.pop(old, None)
                self.failed = self.failed[-6:]
        finally:
            with self.lock:
                self.busy = False

    def get(self, ident):
        with self.lock:
            data = self.jobs.get(ident)
            return dict(data) if data else None


class Handler(FileHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def do_POST(self):
        if self.path != '/api/generate':
            return self.json_response(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        try:
            if origin and (urlparse(origin).scheme not in ('http', 'https') or urlparse(origin).netloc != self.headers.get('Host')):
                return self.json_response(403, {'error': 'Same-origin requests only'})
        except ValueError:
            return self.json_response(403, {'error': 'Invalid origin'})
        if not secrets.compare_digest(self.headers.get('X-Jali-Token', '').encode('utf-8'), self.server.state.token.encode('ascii')):
            return self.json_response(403, {'error': 'Refresh the page to obtain its request token'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192 or self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                raise ValueError('Expected a small JSON body with Content-Length')
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError('Incomplete request')
            payload = json.loads(body)
            if not isinstance(payload, dict) or set(payload) != {'text'}:
                raise ValueError('Expected only a text field')
            validate_request(payload['text'])
        except (ValueError, UnicodeError) as error:
            return self.json_response(400, {'error': str(error)})
        ident = self.server.state.start(payload['text'])
        if ident is None:
            return self.json_response(409, {'error': 'One generation is already running. Please wait.'})
        return self.json_response(202, {'id': ident})

    def do_GET(self, head_only=False):
        route = urlparse(self.path).path
        if route == '/api/config':
            return self.json_response(200, {'token': self.server.state.token, 'max_characters': 500,
                'voice': 'Kokoro af_heart (stock, CPU)', 'rig': self.server.state.rig})
        if route.startswith('/api/jobs/'):
            ident = route[len('/api/jobs/'):]
            result = self.server.state.get(ident) if SESSION_ID.fullmatch(ident) else None
            return self.json_response(200 if result else 404, result or {'error': 'Unknown/expired job'})
        if route in STATIC:
            return self.send_file(self.server.assets / STATIC[route], head_only)
        parts = route.split('/')
        if len(parts) == 4 and parts[1] == 'sessions' and SESSION_ID.fullmatch(parts[2]) and parts[3] in MEDIA:
            result = self.server.state.get(parts[2])
            if result and result['state'] == 'ready':
                return self.send_file(self.server.state.root / parts[2] / parts[3], head_only)
        if route == '/favicon.ico':
            self.send_response(204); self.end_headers(); return
        return self.json_response(404, {'error': 'Not found'})


def make_server(assets, state, host='0.0.0.0', port=8082):
    server = ThreadingHTTPServer((host, port), Handler)
    server.assets, server.state = Path(assets), state
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8082)
    parser.add_argument('--bind', default='0.0.0.0')
    args = parser.parse_args()
    assets = ROOT / 'artifacts/neural-studio'
    required = ['index.html', 'viewer.js', 'controller.js', 'demo-data.js', 'rig.json']
    if not all((assets / name).is_file() for name in required):
        parser.error('Run tools/build_neural_studio.py first')
    rig = json.loads((assets / 'rig.json').read_text())
    if digest(assets / 'viewer.js') != rig['viewer_sha256'] or digest(assets / 'model/mpfb-head.glb') != rig['model_sha256']:
        parser.error('Studio assets changed: rerun build_neural_studio.py')
    verify_assets(ROOT / 'models/kokoro')
    rhubarb = ROOT / '.cache/lipsync/rhubarb/rhubarb'
    if not rhubarb.is_file() or digest(rhubarb) != BINARY_SHA:
        parser.error('Run build_neural_studio.py to explicitly prepare the analyzer')
    # Each launch uses a private run directory: previous runs are not exposed.
    sessions = ROOT / 'artifacts/neural-studio-sessions'
    sessions.mkdir(exist_ok=True)
    # Bound stale disk retention too. Only our UUID-named directories are removed.
    for old in sessions.iterdir():
        if old.is_dir() and SESSION_ID.fullmatch(old.name):
            shutil.rmtree(old)
    state = StudioState(sessions, rig, rhubarb)
    server = make_server(assets, state, args.bind, args.port)
    print(f'Local neural face studio on {args.bind}:{args.port}; CPU only; development server', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.pool.shutdown(wait=True)


if __name__ == '__main__':
    main()
