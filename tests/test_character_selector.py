import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from character_studio_server import make_character_server, close_character_server
from analyze_neural_clips import digest
from package_windows import studio_assets


def studio(root, name):
    path = root / name
    (path / 'model').mkdir(parents=True)
    for f in ('index.html', 'controller.js', 'viewer.js', 'demo-data.js', 'model/low.glb'):
        (path / f).write_text('public transport fixture ' + name)
    (path / 'model/mpfb-head.glb').write_text(name)
    rig = {'profile': name, 'viewer_sha256': digest(path / 'viewer.js'), 'model_sha256': digest(path / 'model/mpfb-head.glb')}
    (path / 'rig.json').write_text(json.dumps(rig))
    return path


class CharacterSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.root = Path(self.temp.name)
        self.female, self.male = (studio(self.root, n) for n in ('female', 'male'))
        self.server = make_character_server(self.female, self.male, self.root / 'sessions', None)
        self.server.RequestHandlerClass.log_message = lambda *_: None
        self.thread = threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.thread.join();close_character_server(self.server);self.temp.cleanup()

    def config(self, name):
        with urlopen(self.url + f'/characters/{name}/api/config') as r:return json.load(r)

    def test_rigs_tokens_and_stores_are_isolated(self):
        f, m = (self.config(n) for n in ('female', 'male'))
        self.assertNotEqual(f['rig']['model_sha256'], m['rig']['model_sha256'])
        self.assertNotEqual(f['token'], m['token'])
        self.assertEqual(m['character'], 'male');self.assertEqual(len(m['characters']), 2)
        self.assertNotEqual(*(v['state'].root for v in self.server.characters.values()))
        request = Request(self.url + '/characters/female/api/cast', data=b'[]', headers={'X-Jali-Token': m['token'], 'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as e:urlopen(request)
        self.assertEqual(e.exception.code, 403)

    def test_global_busy_slot_and_executor(self):
        f, m = (self.server.characters[n]['state'] for n in ('female', 'male'))
        self.assertIs(f.pool, m.pool);self.assertIs(f.lock, m.lock)
        with f.lock:f.busy = True
        self.assertIsNone(m.start('A bounded public test.'))
        self.assertFalse(m.jobs)
        with f.lock:f.busy = False
        self.assertFalse(m.busy)

    def test_no_cross_character_session_lookup(self):
        f = self.server.characters['female']['state'];ident = 'a' * 32
        f.jobs[ident] = {'state': 'ready', 'id': ident}
        with urlopen(self.url + '/characters/female/api/jobs/' + ident) as r:self.assertEqual(json.load(r)['id'], ident)
        with self.assertRaises(HTTPError) as e:urlopen(self.url + '/characters/male/api/jobs/' + ident)
        self.assertEqual(e.exception.code, 404)

    def test_unknown_paths_not_filesystem_mounts(self):
        for path in ('/characters/other/api/config', '/characters/female/rigs/private.json', '/characters/female/model/../private.json'):
            with self.assertRaises(HTTPError) as e:urlopen(self.url + path)
            self.assertEqual(e.exception.code, 404)

    def test_changed_model_refused(self):
        (self.male / 'model/mpfb-head.glb').write_text('tampered')
        with self.assertRaises(ValueError):make_character_server(self.female, self.male, self.root / 'other', None)

    def test_package_positive_allowlist(self):
        (self.male / 'private-session.wav').write_text('never bundle')
        (self.male / 'sessions').mkdir();(self.male / 'sessions/secret.json').write_text('private')
        files = studio_assets(self.male, 'artifacts/neural-studio')
        self.assertTrue(files)
        self.assertFalse(any('private' in f or 'secret' in f for f, _ in files))

    def test_package_symlink_escape_refused(self):
        target = self.root / 'not-a-public-asset';target.write_text('private')
        (self.male / 'viewer.js').unlink()
        try:(self.male / 'viewer.js').symlink_to(target)
        except OSError:self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):studio_assets(self.male, 'artifacts/neural-studio')

    def test_second_bind_cannot_erase_first_server_sessions(self):
        folder=self.root/'sessions/female'/('b'*32);folder.mkdir(parents=True)
        sentinel=folder/'audio.wav';sentinel.write_bytes(b'preserve running session')
        with self.assertRaises(OSError):make_character_server(self.female,self.male,self.root/'sessions',None,port=self.server.server_port)
        self.assertEqual(sentinel.read_bytes(),b'preserve running session')
