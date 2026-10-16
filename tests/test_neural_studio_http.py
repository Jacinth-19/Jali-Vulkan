"""Model-free HTTP/concurrency/retention tests; fake pipeline is explicit here only."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from neural_studio_server import StudioState, make_server


class StudioHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.gate = threading.Event()
        def fake(ident, text, directory, rig, rhubarb, stage):
            directory.mkdir()
            (directory / 'audio.wav').write_bytes(b'RIFF-not-real-audio-contract-test-only')
            stage('analyzing')
            self.gate.wait(3)
            if text == 'fail':
                raise ValueError('Injected failure')
            return {'id': ident, 'text': text}
        self.state = StudioState(self.root / 'sessions', {'test': True}, None, pipeline=fake)
        (self.root / 'index.html').write_text('test-only')
        self.server = make_server(self.root, self.state, '127.0.0.1', 0)
        self.server.RequestHandlerClass.log_message = lambda *args: None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.gate.set()
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.state.pool.shutdown(wait=True)
        self.temp.cleanup()

    def request(self, path, data=None, headers=None, method=None):
        default = {'Content-Type': 'application/json', 'X-Jali-Token': self.state.token}
        default.update(headers or {})
        request = Request(self.base + path, data=data, headers=default, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def post(self, value, **kwargs):
        return self.request('/api/generate', json.dumps(value).encode(), **kwargs)

    def wait(self, ident, state):
        limit = time.monotonic() + 5
        while time.monotonic() < limit:
            result = self.state.get(ident)
            if result and result['state'] == state and (state == 'running' or not self.state.busy):
                return result
            time.sleep(.01)
        self.fail('Test worker did not reach expected state')

    def test_cancel_auth_cleanup_retry_and_terminal_race(self):
        code,data,_=self.post({'text':'Cancel this'})
        self.assertEqual(code,202);ident=json.loads(data)['id'];self.wait(ident,'running')
        def cancel(headers=None):return self.request('/api/cancel',json.dumps({'id':ident}).encode(),headers=headers)
        self.assertEqual(cancel({'Origin':'https://other.invalid'})[0],403)
        self.assertEqual(cancel({'X-Jali-Token':''})[0],403)
        self.assertEqual(cancel()[0],202);self.assertEqual(cancel()[0],202)
        self.assertTrue(self.state.busy)
        self.assertEqual(self.post({'text':'Not yet'})[0],409)
        self.assertEqual(self.request(f'/sessions/{ident}/audio.wav')[0],404)
        self.gate.set();self.wait(ident,'cancelled')
        self.assertFalse((self.state.root/ident).exists());self.assertNotIn(ident,self.state.ready)
        self.assertEqual(cancel()[0],409)
        code,data,_=self.post({'text':'Retry after cancellation'});self.assertEqual(code,202)
        ready_id=json.loads(data)['id'];self.wait(ready_id,'ready')
        # Simulate the tiny ready-publication/finally window: even a retained
        # token must not turn a ready job into a forever-cancelling job.
        from neural_cancel import CancellationToken
        self.state.tokens[ready_id]=CancellationToken()
        self.assertFalse(self.state.cancel(ready_id));self.assertEqual(self.state.get(ready_id)['state'],'ready')
        self.state.tokens.pop(ready_id)

    def test_cancel_invalid_unknown_and_invalid_unicode(self):
        for payload in ({'id':'../escape'},{'id':[]},{'id':'a'*32,'extra':True}):
            self.assertEqual(self.request('/api/cancel',json.dumps(payload).encode())[0],400)
        self.assertEqual(self.request('/api/cancel',json.dumps({'id':'a'*32}).encode())[0],404)
        self.assertEqual(self.post({'text':'bad\ud800'})[0],400)
        self.assertFalse(self.state.busy)

    def test_stream_and_ack_route_validation_and_csrf(self):
        for route in ('/api/stream','/api/ack'):
            self.assertEqual(self.request(route,b'{}',headers={'X-Jali-Token':''})[0],403)
        self.assertEqual(self.request('/api/stream',json.dumps({'text':'Hi. '*10}).encode())[0],400)
        for index in (-1,True,.5,8,'0'):
            self.assertEqual(self.request('/api/ack',json.dumps({'id':'a'*32,'index':index}).encode())[0],400)
        self.assertEqual(self.request('/api/ack',json.dumps({'id':'a'*32,'index':0}).encode())[0],404)
        self.assertFalse(self.state.busy)

    def test_optional_native_frame_auth_query_and_expired_identity(self):
        self.assertEqual(self.request('/api/native/frame?id=neutral&time=0')[0],404)
        from types import SimpleNamespace
        self.state.native=SimpleNamespace(metadata={'fixture':True},frame=lambda clip,query:(b'explicit-test-image-fixture',1.25))
        route='/api/native/frame?id=neutral&time=0'
        self.assertEqual(self.request(route,headers={'X-Jali-Token':''})[0],403)
        self.assertEqual(self.request(route,headers={'Origin':'https://other.invalid'})[0],403)
        self.assertEqual(self.request(route+'&time=1')[0],400)
        self.assertEqual(self.request(route+'&model_url=bad')[0],400)
        self.assertEqual(self.request('/api/native/frame?id=unknown&time=0')[0],404)
        code,body,headers=self.request(route);self.assertEqual((code,body),(200,b'explicit-test-image-fixture'));self.assertEqual(headers['X-Jali-Render-Ms'],'1.250')

    def test_config_and_root(self):
        code, data, headers = self.request('/api/config')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)['token'], self.state.token)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.request('/')[1], b'test-only')

    def test_same_origin_and_token_checks(self):
        self.assertEqual(self.post({'text': 'Hi'}, headers={'Origin': 'https://other.invalid'})[0], 403)
        self.assertEqual(self.post({'text': 'Hi'}, headers={'X-Jali-Token': ''})[0], 403)
        self.assertFalse(self.state.busy)

    def test_input_bounds_and_no_extra_fields(self):
        for payload in ({'text': ''}, {'text': 'x' * 501}, {'text': []}, {'text': 'Hi', 'model_url': 'external'}, []):
            with self.subTest(payload=str(payload)[:30]):
                self.assertEqual(self.post(payload)[0], 400)
        self.assertEqual(self.request('/api/generate', b'bad-json')[0], 400)
        self.assertEqual(self.request('/api/generate', b'x' * 8193)[0], 400)
        self.assertFalse(self.state.busy)

    def test_one_job_and_media_not_public_until_ready(self):
        code, data, _ = self.post({'text': 'Hi'})
        self.assertEqual(code, 202); ident = json.loads(data)['id']
        self.wait(ident, 'running')
        self.assertEqual(self.post({'text': 'Another request'})[0], 409)
        self.assertEqual(self.request(f'/sessions/{ident}/audio.wav')[0], 404)
        self.gate.set(); self.wait(ident, 'ready')
        self.assertEqual(self.request(f'/api/jobs/{ident}')[0], 200)
        code, data, headers = self.request(f'/sessions/{ident}/audio.wav', headers={'Range': 'bytes=0-3'})
        self.assertEqual((code, data), (206, b'RIFF'))
        self.assertTrue(headers['Content-Range'].startswith('bytes 0-3/'))
        self.assertEqual(self.request(f'/sessions/{ident}/worker.log')[0], 404)

    def test_failed_job_never_becomes_a_ready_fallback(self):
        self.gate.set()
        ident = json.loads(self.post({'text': 'fail'})[1])['id']
        result = self.wait(ident, 'error')
        self.assertNotIn('clip', result)
        self.assertFalse((self.state.root / ident).exists())
        self.assertEqual(self.request(f'/sessions/{ident}/audio.wav')[0], 404)
        retry = json.loads(self.post({'text': 'Good retry'})[1])['id']
        self.wait(retry, 'ready')

    def test_paths_and_private_assets_not_served(self):
        for path in ('/models/kokoro/model_quantized.onnx', '/../../.git/config', '/sessions/../audio.wav',
                     '/api/jobs/../escape', '/sessions/'+'a'*32+'/../../.git/config'):
            self.assertEqual(self.request(path)[0], 404)

    def test_six_ready_sessions_retained(self):
        self.gate.set(); ids=[]
        for index in range(7):
            ident = self.state.start(f'Test {index}'); self.wait(ident, 'ready'); ids.append(ident)
        self.assertEqual(len(self.state.ready), 6)
        self.assertIsNone(self.state.get(ids[0]))
        self.assertFalse((self.state.root / ids[0]).exists())
        self.assertTrue((self.state.root / ids[-1]).exists())


if __name__ == '__main__':
    unittest.main()
