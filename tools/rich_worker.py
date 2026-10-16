"""Bounded cross-platform persistent native named-morph worker (no speech)."""
import json
import queue
import subprocess
import threading
import time
from pathlib import Path
from render_session import ROOT,runtime_environment


class RichWorker:
    def __init__(self,asset,output,software=False,size=512,test=False):
        self.lock=threading.Lock();self.messages=queue.Queue(maxsize=2);self.closed=threading.Event()
        output=Path(output);output.mkdir(parents=True,exist_ok=True);self.log=(output/'engine.log').open('wb')
        binary=ROOT/('build-live/jali_rich.exe' if __import__('os').name=='nt' else 'build-live/jali_rich')
        args=[str(binary),'--asset',str(asset),'--output',str(output),'--size',str(size)]
        if test:args.append('--test')
        try:self.process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,bufsize=0,env=runtime_environment(software))
        except BaseException:self.log.close();raise
        self.thread=threading.Thread(target=self._read,args=(size,),daemon=True);self.thread.start()
        try:self.metadata=json.loads(self._message(60))
        except BaseException:self.close();raise
    def _read(self,size):
        def put(item):
            while not self.closed.is_set():
                try:self.messages.put(item,timeout=.1);return
                except queue.Full:pass
        try:
            line=self.process.stdout.readline(16385)
            if not line.endswith(b'\n') or len(line)>16384:raise RuntimeError('Invalid native metadata')
            put(line)
            while not self.closed.is_set():
                data=bytearray()
                while len(data)<size*size*4:
                    block=self.process.stdout.read(min(65536,size*size*4-len(data)))
                    if not block:raise RuntimeError('Native renderer exited; inspect engine.log')
                    data.extend(block)
                put(bytes(data))
        except BaseException as e:put(e)
    def _message(self,timeout):
        try:item=self.messages.get(timeout=timeout)
        except queue.Empty:raise TimeoutError('Native renderer response timed out') from None
        if isinstance(item,BaseException):raise item
        return item
    def frame(self,weights,motion=None):
        if not self.lock.acquire(blocking=False):raise BlockingIOError('One native frame is already pending')
        try:
            if self.closed.is_set():raise RuntimeError('Native renderer closed')
            began=time.perf_counter();self.process.stdin.write((json.dumps({'weights':weights,'motion':motion} if motion is not None else weights,allow_nan=False)+'\n').encode());self.process.stdin.flush()
            return self._message(30),(time.perf_counter()-began)*1000
        except BaseException:self.close();raise
        finally:self.lock.release()
    def close(self):
        if self.closed.is_set():return
        self.closed.set()
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
        self.thread.join(timeout=3)
        self.process.stdin.close();self.process.stdout.close();self.log.close()
