"""HTTP safety/range contracts; no GPU, speech library, or Python packages needed."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import preview_server


class QuietHandler(preview_server.Handler):
    def log_message(self, *args):
        pass


class FakeLive:
    def status(self): return {"id":"b"*32,"mode":"live-mesh"}
    def prepare(self, text): return {"id":"b"*32,"text":text}
    def frame(self, session_id, seconds):
        if session_id != "b"*32: raise LookupError("Session expired")
        if not math.isfinite(seconds) or not 0<=seconds<=10: raise ValueError("invalid audio time")
        return b"jpeg-test-payload", 2.5


class PreviewHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.root_patch = patch.object(preview_server, "ROOT", cls.root)
        cls.root_patch.start()
        (cls.root / "web").mkdir()
        (cls.root / "web/index.html").write_text("Jali preview")
        (cls.root / "artifacts/live-demo").mkdir(parents=True)
        (cls.root / "artifacts/live-demo/session.mp4").write_bytes(b"0123456789")
        (cls.root / "artifacts/live-demo/session.json").write_text(json.dumps({"voice": "espeak"}))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.server.state = preview_server.PreviewState()
        cls.server.live = FakeLive()
        cls.server.state.start = Mock(return_value="a" * 32)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server.state.executor.shutdown()
        cls.thread.join()
        cls.root_patch.stop()
        cls.temp.cleanup()

    def request(self, method, route, data=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, route, body=data, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def post(self, value, extra=None):
        headers = {"Content-Type": "application/json"}
        headers.update(extra or {})
        return self.request("POST", "/api/render", json.dumps(value), headers)

    def test_index(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"Jali preview")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_latest_metadata(self):
        status, _, body = self.request("GET", "/api/session")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["session"]["video_url"], "/media/live-demo/session.mp4")

    def test_valid_request(self):
        self.assertEqual(self.post({"text": "Speak this line."})[0], 202)

    def test_blank_or_extra_fields_rejected(self):
        for value in ({"text": " "}, {"text": "a\0b"}, {"text": "a" * 241},
                      {"text": "✓" * 81}, {"text": "hello", "command": "anything"},
                      {"text": 42}, [], {}):
            with self.subTest(value=value):
                self.assertEqual(self.post(value)[0], 400)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.post({"text": "hello"}, {"Origin": "https://untrusted.example"})[0], 403)

    def test_busy_is_conflict(self):
        with patch.object(self.server.state, "start", return_value=None):
            self.assertEqual(self.post({"text": "hello"})[0], 409)

    def test_no_repository_or_arbitrary_media_access(self):
        for route in ("/.git/config", "/media/live-demo/../../README.md", "/media/live-demo/frames.rgba", "/media/not-a-session/session.mp4"):
            self.assertEqual(self.request("GET", route)[0], 404)

    def test_byte_ranges_for_seeking(self):
        status, headers, body = self.request("GET", "/media/live-demo/session.mp4", headers={"Range": "bytes=2-4"})
        self.assertEqual(status, 206)
        self.assertEqual(body, b"234")
        self.assertEqual(headers["Content-Range"], "bytes 2-4/10")
        self.assertEqual(self.request("GET", "/media/live-demo/session.mp4", headers={"Range": "bytes=-2"})[2], b"89")

    def test_invalid_ranges_rejected(self):
        for value in ("bytes=20-", "bytes=4-2", "bytes=-", "bytes=0-1,4-6", "items=0-2"):
            self.assertEqual(self.request("GET", "/media/live-demo/session.mp4", headers={"Range": value})[0], 416)

    def test_head_has_no_body(self):
        status, headers, body = self.request("HEAD", "/media/live-demo/session.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Length"], "10")
        self.assertEqual(body, b"")

    def test_live_status_and_creation(self):
        status, _, body=self.request("GET","/api/live/session")
        self.assertEqual(status,200);self.assertEqual(json.loads(body)["session"]["mode"],"live-mesh")
        status, _, body=self.request("POST","/api/live/session",json.dumps({"text":"Hello"}),{"Content-Type":"application/json"})
        self.assertEqual(status,201);self.assertEqual(json.loads(body)["session"]["text"],"Hello")

    def test_live_frame_headers_and_payload(self):
        status,headers,body=self.request("GET","/api/live/frame?id="+"b"*32+"&time=0.5")
        self.assertEqual(status,200);self.assertEqual(headers["Content-Type"],"image/jpeg")
        self.assertEqual(headers["X-Audio-Time"],"0.500000000");self.assertEqual(headers["Cache-Control"],"no-store")
        self.assertEqual(body,b"jpeg-test-payload")

    def test_live_bad_timestamps_and_schema(self):
        for query in ("id="+"b"*32+"&time=nan", "id="+"b"*32+"&time=-1", "id="+"b"*32+"&time=11",
                      "id="+"b"*32+"&time=1&time=2", "time=0.5", "id=../private&time=0"):
            self.assertEqual(self.request("GET","/api/live/frame?"+query)[0],400)

    def test_live_expired_session(self):
        self.assertEqual(self.request("GET","/api/live/frame?id="+"c"*32+"&time=0")[0],410)

    def test_live_frame_backpressure(self):
        with patch.object(self.server.live,"frame",side_effect=BlockingIOError("frame busy")):
            self.assertEqual(self.request("GET","/api/live/frame?id="+"b"*32+"&time=0")[0],409)
