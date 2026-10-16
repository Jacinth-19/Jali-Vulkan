"""Cooperative cancellation of only the speech/analyzer child owned by a job."""
import subprocess
import threading
import time


class GenerationCancelled(Exception):
    pass


class CancellationToken:
    def __init__(self):
        self.event=threading.Event();self.lock=threading.Lock();self.process=None

    def check(self):
        if self.event.is_set():raise GenerationCancelled('Generation cancelled')

    def cancel(self):
        self.event.set()
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                try:self.process.terminate()
                except ProcessLookupError:pass

    def run(self, command, *, check=True, capture_output=True, timeout=90, **kwargs):
        if not capture_output:raise ValueError('Cancellation runner requires captured output')
        self.check();started=time.monotonic()
        with self.lock:
            self.check()
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)
            self.process=process
        try:
            while True:
                if self.event.is_set():
                    if process.poll() is None:process.kill()
                    process.communicate(timeout=5)
                    raise GenerationCancelled('Generation cancelled')
                remaining=timeout-(time.monotonic()-started)
                if remaining<=0:
                    process.kill();process.communicate(timeout=5)
                    raise subprocess.TimeoutExpired(command,timeout)
                try:
                    out,err=process.communicate(timeout=min(.1,remaining));break
                except subprocess.TimeoutExpired:pass
            self.check()
            if check and process.returncode:raise subprocess.CalledProcessError(process.returncode,command,out,err)
            return subprocess.CompletedProcess(command,process.returncode,out,err)
        finally:
            if process.poll() is None:
                process.kill();process.communicate(timeout=5)
            with self.lock:self.process=None
