#!/usr/bin/env python3
"""Development-only preview server. No cloud APIs, uploads, or arbitrary commands."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import shutil
import threading
from urllib.parse import urlparse, parse_qs
import uuid

from render_session import ROOT, render_session
from live_session import LiveState

MEDIA_FILES = {"session.mp4", "poster.jpg", "session.wav", "face.csv", "metrics.json", "session.json", "phonemes.json"}
SESSION_ID = re.compile(r"(?:live-demo|[a-f0-9]{32})\Z")


class PreviewState:
    def __init__(self, binary=None, software=False):
        self.binary = binary
        self.software = software
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.busy = False
        self.jobs = {}
        self.latest = "live-demo" if (ROOT / "artifacts/live-demo/session.mp4").is_file() else None
        self.completed = []

    def metadata(self, session_id):
        if not session_id:
            return None
        data = json.loads((ROOT / "artifacts" / session_id / "session.json").read_text())
        data["id"] = session_id
        data["video_url"] = f"/media/{session_id}/session.mp4"
        data["poster_url"] = f"/media/{session_id}/poster.jpg"
        return data

    def start(self, text):
        with self.lock:
            if self.busy:
                return None
            self.busy = True
            session_id = uuid.uuid4().hex
            self.jobs[session_id] = {"state": "running", "stage": "Preparing local engines"}
        self.executor.submit(self.render, session_id, text)
        return session_id

    def render(self, session_id, text):
        directory = ROOT / "artifacts" / session_id
        def stage(message):
            with self.lock:
                self.jobs[session_id]["stage"] = message
        try:
            render_session(directory, text, self.binary, self.software, on_stage=stage)
            with self.lock:
                self.latest = session_id
                self.jobs[session_id] = {"state": "ready", "session": self.metadata(session_id)}
                self.completed.append(session_id)
                # Bound both disk use and job records. Never delete the bundled initial demo.
                while len(self.completed) > 5:
                    old = self.completed.pop(0)
                    shutil.rmtree(ROOT / "artifacts" / old)
                    self.jobs.pop(old, None)
        except Exception as error:
            shutil.rmtree(directory, ignore_errors=True)
            with self.lock:
                self.jobs[session_id] = {"state": "error", "error": str(error)[-1000:]}
                failed = [key for key, value in self.jobs.items() if value["state"] == "error"]
                for old in failed[:-5]:
                    self.jobs.pop(old, None)
        finally:
            with self.lock:
                self.busy = False


class Handler(BaseHTTPRequestHandler):
    server_version = "JaliPreview/0.1"

    def log_message(self, format, *args):
        # Do not fill the development log with every successful live frame.
        if self.path.startswith("/api/live/frame") and len(args) > 1 and args[1] == "200":
            return
        super().log_message(format, *args)

    def json_response(self, status, data):
        raw = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def do_POST(self):
        if self.path not in ("/api/render", "/api/live/session"):
            return self.json_response(404, {"error": "Not found"})
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.json_response(403, {"error": "Same-origin requests only"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096 or self.headers.get_content_type() != "application/json":
                raise ValueError("Expected a small JSON request")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {"text"}:
                raise ValueError("Expected only a text field")
            text = payload["text"]
            if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 240 or "\0" in text:
                raise ValueError("Enter 1-240 UTF-8 bytes of nonblank text without NUL")
        except (ValueError, UnicodeError) as error:
            return self.json_response(400, {"error": str(error)})
        if self.path == "/api/live/session":
            try:
                return self.json_response(201, {"session": self.server.live.prepare(text)})
            except BlockingIOError as error:
                return self.json_response(409, {"error": str(error)})
            except ValueError as error:
                return self.json_response(400, {"error": str(error)})
            except Exception as error:
                return self.json_response(503, {"error": str(error)[-1000:]})
        session_id = self.server.state.start(text)
        if session_id is None:
            return self.json_response(409, {"error": "A render is already in progress. Please wait."})
        return self.json_response(202, {"id": session_id})

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only=False):
        route = urlparse(self.path).path
        if route == "/api/live/session":
            try:
                return self.json_response(200, {"session": self.server.live.status()})
            except BlockingIOError as error:
                return self.json_response(409, {"error": str(error)})
        if route == "/api/live/frame":
            try:
                query = parse_qs(urlparse(self.path).query, strict_parsing=True)
                if set(query) != {"id", "time"} or any(len(v)!=1 for v in query.values()):
                    raise ValueError("Frame request requires one id and one time")
                session_id=query["id"][0]
                if not SESSION_ID.fullmatch(session_id):
                    raise ValueError("Invalid session id")
                seconds=float(query["time"][0])
                raw, render_ms=self.server.live.frame(session_id, seconds)
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Audio-Time", f"{seconds:.9f}")
                self.send_header("X-Render-Ms", f"{render_ms:.3f}")
                self.end_headers()
                if not head_only:
                    self.wfile.write(raw)
                return
            except (ValueError, KeyError) as error:
                return self.json_response(400, {"error": str(error)})
            except BlockingIOError as error:
                return self.json_response(409, {"error": str(error)})
            except LookupError as error:
                return self.json_response(410, {"error": str(error)})
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as error:
                return self.json_response(503, {"error": str(error)[-1000:]})
        if route == "/api/session":
            with self.server.state.lock:
                data = self.server.state.metadata(self.server.state.latest)
            return self.json_response(200, {"session": data})
        if route.startswith("/api/jobs/"):
            session_id = route[len("/api/jobs/"):]
            with self.server.state.lock:
                result = self.server.state.jobs.get(session_id)
            return self.json_response(200 if result else 404, result or {"error": "Unknown job"})
        static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if route in static:
            return self.send_file(ROOT / "web" / static[route], head_only)
        parts = route.split("/")
        if len(parts) == 4 and parts[1] == "media" and SESSION_ID.fullmatch(parts[2]) and parts[3] in MEDIA_FILES:
            return self.send_file(ROOT / "artifacts" / parts[2] / parts[3], head_only)
        return self.json_response(404, {"error": "Not found"})

    def send_file(self, path, head_only):
        try:
            stream = path.open("rb")
        except OSError:
            return self.json_response(404, {"error": "File not found"})
        with stream:
            size = path.stat().st_size
            start, end = 0, size - 1
            requested = self.headers.get("Range")
            if requested:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
                if not match or not any(match.groups()):
                    self.send_error(416)
                    return
                left, right = match.groups()
                if left:
                    start = int(left)
                    if right:
                        end = min(int(right), end)
                else:
                    start = max(0, size - int(right))
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            self.send_response(206 if requested else 200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-cache")
            if requested:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if head_only:
                return
            stream.seek(start)
            remaining = end - start + 1
            try:
                while remaining:
                    block = stream.read(min(65536, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError):
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--software-vulkan", action="store_true")
    parser.add_argument("--require-hardware", action="store_true", help="Reject software Vulkan instead of silently falling back")
    args = parser.parse_args()
    if args.require_hardware and args.software_vulkan:
        parser.error("--require-hardware cannot be combined with --software-vulkan")
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.state = PreviewState(args.binary, args.software_vulkan)
    server.live = LiveState(args.software_vulkan, args.require_hardware)
    try:
        server.live.prepare("Hello. I am Jali. My imported character follows phonemes, rendered live with Vulkan.")
    except Exception as error:
        print(f"Live session unavailable: {error}", flush=True)
    print(f"Jali preview listening on 0.0.0.0:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.live.close()
        server.state.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
