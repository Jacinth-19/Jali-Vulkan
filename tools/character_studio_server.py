"""Two explicitly prepared, rig-isolated studios; one shared CPU inference slot.

An exclusive browser Web Lock serializes renderer ownership across this origin
and browser profile. Switching disposes the old renderer before releasing the
lock and navigating. Different origins/profiles/apps remain separate.
No runtime external assets/model downloads, geometry rebinding or implicit native fallback.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shutil
from pathlib import Path
import secrets
import threading
from types import SimpleNamespace
from urllib.parse import urlparse

from neural_studio_server import Handler, StudioHTTPServer, StudioState
from analyze_neural_clips import digest, verify_engine
from local_neural_speech import verify_assets
from neural_platform import analyzer_path
from runtime_paths import ASSET_ROOT
from studio_workspace import ControlBroker
from neural_session import SESSION_ID


class Budget:
    def __init__(self):
        self.busy = False
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)


class CharacterState(StudioState):
    @property
    def busy(self):
        return self.budget.busy

    @busy.setter
    def busy(self, value):
        self.budget.busy = value

    def __init__(self, budget, *args, **kwargs):
        self.budget = budget
        super().__init__(*args, **kwargs)
        self.pool.shutdown(wait=True)
        self.pool = budget.pool
        self.lock = budget.lock
        self.condition = threading.Condition(self.lock)


def prepared_rig(assets):
    assets = Path(assets)
    for name in ('index.html', 'controller.js', 'viewer.js', 'demo-data.js', 'rig.json', 'model/low.glb'):
        if not (assets / name).is_file():
            raise ValueError('Missing prepared character asset: ' + name)
    rig = json.loads((assets / 'rig.json').read_text())
    if digest(assets / 'viewer.js') != rig['viewer_sha256'] or digest(assets / 'model/mpfb-head.glb') != rig['model_sha256']:
        raise ValueError('Prepared character bytes differ from rig binding')
    return rig


class CharacterHandler(Handler):
    def json_response(self, status, data):
        if urlparse(self.path).path == '/api/config' and status == 200:
            data = {**data, 'voice': 'Kokoro stock CPU: '+self.server.state.cast[0]['voice'], 'character': self.character, 'characters': [
                {'id': name, 'name': name.title()} for name in ('female', 'male')],
                'resource_scope': 'One character renderer per origin/browser profile; other tabs wait before model fetch/decode. One shared CPU job. Different origins/profiles/apps remain separate.'}
        return super().json_response(status, data)

    def dispatch(self, method, head_only=False):
        original_server, original_path = self.server, self.path
        route = urlparse(self.path).path
        if route == '/':
            self.send_response(302)
            self.send_header('Location', '/characters/male/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if route.startswith('/characters/'):
            parts = self.path.split('/', 3)
            if len(parts) != 4 or parts[2] not in original_server.characters:
                return super().json_response(404, {'error': 'Unknown character route'})
            name, rest = parts[2], '/' + parts[3]
        else:
            # Backwards-compatible root API alias for the default (male) rig.
            # It does not select a rig from a cookie/global mutable server state.
            name, rest = 'male', self.path
        self.character = name
        entry = original_server.characters[name]
        self.server = SimpleNamespace(state=entry['state'], assets=entry['assets'])
        self.path = rest
        try:
            if method == 'POST':
                return super().do_POST()
            return super().do_GET(head_only)
        finally:
            self.server, self.path = original_server, original_path

    def do_GET(self, head_only=False):
        return self.dispatch('GET', head_only)

    def do_HEAD(self):
        return self.dispatch('GET', True)

    def do_POST(self):
        return self.dispatch('POST')


def make_character_server(female, male, sessions, rhubarb, host='127.0.0.1', port=0, pipeline=None, integration_key=None):
    rigs = {name: prepared_rig(assets) for name, assets in [('female', female), ('male', male)]}
    if rigs['female']['model_sha256'] == rigs['male']['model_sha256']:
        raise ValueError('Character pair must contain two distinct prepared models')
    budget = Budget()
    states = []
    server = None
    try:
        server = StudioHTTPServer((host, port), CharacterHandler)
        server.budget, server.characters = budget, {}
        for name, assets in [('female', female), ('male', male)]:
            kwargs = {'pipeline': pipeline} if pipeline else {}
            state = CharacterState(budget, Path(sessions) / name, rigs[name], rhubarb, **kwargs)
            states.append(state)
            # Match the single-rig ephemeral-session policy; saved conversations
            # live outside these UUID folders and are never deleted here.
            for old in state.root.iterdir():
                if SESSION_ID.fullmatch(old.name) and old.is_dir() and not old.is_symlink():shutil.rmtree(old)
            if name=='male' and not state.cast_file.exists() and 'am_michael' in state.voices:
                state.cast[0]['voice']='am_michael'
            if integration_key:
                state.control = ControlBroker(integration_key)
            server.characters[name] = {'assets': Path(assets), 'state': state}
        return server
    except BaseException:
        if server: server.server_close()
        for state in states: state.cancel_active()
        budget.pool.shutdown(wait=True)
        raise


def close_character_server(server):
    server.server_close()
    for entry in server.characters.values():
        entry['state'].cancel_active()
    server.budget.pool.shutdown(wait=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--female', type=Path, required=True)
    p.add_argument('--male', type=Path, required=True)
    p.add_argument('--sessions', type=Path, required=True)
    p.add_argument('--bind', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8082)
    p.add_argument('--ready-file', type=Path)
    p.add_argument('--integration-key-file', type=Path)
    a = p.parse_args()
    verify_assets(ASSET_ROOT / 'models/kokoro')
    rhubarb = analyzer_path(); verify_engine(rhubarb)
    key = None
    if a.integration_key_file:
        if a.bind != '127.0.0.1': p.error('Integration is loopback only')
        a.integration_key_file.parent.mkdir(parents=True, exist_ok=True)
        if not a.integration_key_file.exists():
            fd=os.open(a.integration_key_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(secrets.token_hex(32))
        key = a.integration_key_file.read_text().strip()
        if len(key) != 64 or any(c not in '0123456789abcdef' for c in key): p.error('Invalid integration key')
    server = make_character_server(a.female, a.male, a.sessions, rhubarb, a.bind, a.port, integration_key=key)
    try:
        if a.ready_file:
            a.ready_file.write_text(json.dumps({'port': server.server_port}), encoding='utf-8')
        print(f'Character selector on {a.bind}:{server.server_port}; one shared CPU slot', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        close_character_server(server)


if __name__ == '__main__':
    main()
