"""Bounded persistent native renderer: audio-clock requests, not pre-rendered video."""
import io
import json
import math
import os
from pathlib import Path
import select
import subprocess
import threading
import time
import uuid

from render_session import ROOT, runtime_environment


class LiveWorker:
    def __init__(self, text, software=False, require_hardware=False, binary=None):
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 240 or '\0' in text:
            raise ValueError('Enter 1-240 UTF-8 bytes of nonblank text without NUL')
        self.id = uuid.uuid4().hex
        self.directory = ROOT / 'artifacts' / self.id
        self.directory.mkdir(parents=True)
        self.lock = threading.Lock()
        self.process = None
        self.stderr_file = (self.directory / 'engine.log').open('wb')
        command = [str(binary or ROOT / 'build-live/jali_live'), '--output', str(self.directory), '--text', text]
        if require_hardware:
            command.append('--require-hardware')
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=self.stderr_file, bufsize=0, env=runtime_environment(software))
            ready = self.read_line(20)
            self.metadata = json.loads(ready)
            self.metadata.update(id=self.id, audio_url=f'/media/{self.id}/session.wav',
                                 cues_url=f'/media/{self.id}/phonemes.json')
        except Exception:
            self.close()
            import shutil
            shutil.rmtree(self.directory, ignore_errors=True)
            raise

    def read_line(self, timeout):
        deadline = time.monotonic() + timeout
        line = bytearray()
        while len(line) < 16384:
            block = self.read_exact(1, max(0.001, deadline-time.monotonic()))
            if block == b'\n':
                return bytes(line)
            line.extend(block)
        raise RuntimeError('Native metadata exceeds limit')

    def read_exact(self, size, timeout=10):
        deadline = time.monotonic() + timeout
        data = bytearray()
        while len(data) < size:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise TimeoutError('Native frame response timed out')
            chunk = os.read(self.process.stdout.fileno(), min(65536, size-len(data)))
            if not chunk:
                message = (self.directory / 'engine.log').read_text(errors='replace')[-1000:]
                raise RuntimeError(message or 'Native renderer exited')
            data.extend(chunk)
        return bytes(data)

    def frame(self, seconds):
        from PIL import Image
        if not math.isfinite(seconds) or not 0 <= seconds <= self.metadata['duration_seconds']:
            raise ValueError('Frame time must lie inside the audio duration')
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('A frame is already being rendered')
        try:
            started = time.monotonic()
            if not self.process or self.process.poll() is not None:
                raise RuntimeError('Live renderer is no longer running')
            self.process.stdin.write(f'{seconds:.9f}\n'.encode())
            self.process.stdin.flush()
            size = self.metadata['width'], self.metadata['height']
            raw = self.read_exact(size[0]*size[1]*4)
            encoded = io.BytesIO()
            Image.frombytes('RGBA', size, raw).convert('RGB').save(encoded, format='JPEG', quality=88)
            return encoded.getvalue(), (time.monotonic()-started)*1000
        except (BrokenPipeError, TimeoutError, RuntimeError):
            self.close_locked()
            raise
        finally:
            self.lock.release()

    def close_locked(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            if self.process.stdin:
                self.process.stdin.close()
            if self.process.stdout:
                self.process.stdout.close()
            self.process = None
        self.stderr_file.close()

    def close(self):
        with self.lock:
            self.close_locked()


class LiveState:
    def __init__(self, software=False, require_hardware=False):
        self.software, self.require_hardware = software, require_hardware
        self.lock = threading.Lock()
        self.worker = None
        self.history = []

    def prepare(self, text):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('A live session is already being prepared')
        try:
            if self.worker:
                self.worker.close()
                self.worker = None
            worker = LiveWorker(text, self.software, self.require_hardware)
            self.worker = worker
            self.history.append(worker.directory)
            while len(self.history) > 5:
                import shutil
                shutil.rmtree(self.history.pop(0), ignore_errors=True)
            return worker.metadata
        finally:
            self.lock.release()

    def status(self):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Session is being prepared')
        try:
            return self.worker.metadata if self.worker else None
        finally:
            self.lock.release()

    def frame(self, session_id, seconds):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Session is being prepared')
        try:
            if not self.worker or self.worker.id != session_id:
                raise LookupError('Session expired; prepare a new live session')
            return self.worker.frame(seconds)
        finally:
            self.lock.release()

    def close(self):
        with self.lock:
            if self.worker:
                self.worker.close()
                self.worker = None
