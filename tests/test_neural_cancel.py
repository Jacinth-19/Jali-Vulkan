"""Actual subprocess cancellation/timeout tests, no model or fake child process."""
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_cancel import CancellationToken, GenerationCancelled


class CancellationTests(unittest.TestCase):
    def test_real_owned_child_killed_and_reaped(self):
        token=CancellationToken();errors=[]
        def work():
            try:token.run([sys.executable,'-c','import time;time.sleep(60)'],timeout=70)
            except Exception as e:errors.append(e)
        t=threading.Thread(target=work);t.start()
        limit=time.monotonic()+5
        while token.process is None and time.monotonic()<limit:time.sleep(.01)
        child=token.process;self.assertIsNotNone(child)
        started=time.monotonic();token.cancel();t.join(5)
        self.assertFalse(t.is_alive());self.assertLess(time.monotonic()-started,5)
        self.assertIsNotNone(child.poll());self.assertIsNone(token.process)
        self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],GenerationCancelled)
        with self.assertRaises(GenerationCancelled):token.run([sys.executable,'-c','pass'])

    def test_timeout_failure_and_success_are_distinct(self):
        token=CancellationToken()
        with self.assertRaises(subprocess.TimeoutExpired):token.run([sys.executable,'-c','import time;time.sleep(60)'],timeout=.15)
        self.assertIsNone(token.process)
        with self.assertRaises(subprocess.CalledProcessError):token.run([sys.executable,'-c','raise SystemExit(2)'])
        self.assertEqual(token.run([sys.executable,'-c','print("ok")']).stdout.strip(),b'ok')
