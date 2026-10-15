import csv
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

from analyze_sync import analyze


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audio = Path(self.temp.name) / "session.wav"
        self.curves = Path(self.temp.name) / "face.csv"
        self.write_audio()
        self.write_curves([(0, 0), (0.2, 0.8), (0.3, 0)])

    def write_audio(self, silent=False, channels=1):
        values = [0] * 200 + [0 if silent else 10000] * 300
        with wave.open(str(self.audio), "wb") as wav:
            wav.setparams((channels, 2, 1000, 0, "NONE", "not compressed"))
            wav.writeframes(struct.pack("<" + "h" * len(values), *values))

    def write_curves(self, rows):
        with self.curves.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["audio_time_seconds", "jaw_open"])
            writer.writerows(rows)

    def test_aligned(self):
        self.assertTrue(analyze(self.audio, self.curves, 0)["passed"])

    def test_delayed_and_early_fail(self):
        for onset in (0.05, 0.35):
            with self.subTest(onset=onset):
                self.write_curves([(0, 0), (onset, 0.8)])
                result = analyze(self.audio, self.curves, 100)
                self.assertFalse(result["passed"])
                self.assertAlmostEqual(result["signed_lag_ms"], (onset - 0.2) * 1000)

    def test_exact_boundary_passes(self):
        self.write_curves([(0, 0), (0.3, 0.8)])
        self.assertTrue(analyze(self.audio, self.curves, 100)["passed"])

    def test_silence_is_inconclusive(self):
        self.write_audio(silent=True)
        with self.assertRaises(ValueError):
            analyze(self.audio, self.curves, 100)

    def test_invalid_curves(self):
        cases = [[], [(0, 0)], [(0, 0), (0, 0.8)], [(0.2, 0.8), (0.1, 0)],
                 [(float("nan"), 0.8)], [(0, float("inf"))], [(-0.1, 0.8)],
                 [(0, -0.1)], [(0, 1.1)], [(0.5, 0.8)], [(0, "bad")]]
        for rows in cases:
            with self.subTest(rows=rows):
                self.write_curves(rows)
                with self.assertRaises(ValueError):
                    analyze(self.audio, self.curves, 100)

    def test_bad_schema(self):
        self.curves.write_text("time,mouth\n0,1\n")
        with self.assertRaises(ValueError):
            analyze(self.audio, self.curves, 100)

    def test_invalid_tolerances(self):
        for tolerance in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                analyze(self.audio, self.curves, tolerance)

    def test_stereo_rejected(self):
        self.write_audio(channels=2)
        with self.assertRaises(ValueError):
            analyze(self.audio, self.curves, 100)

    def test_truncated_audio_rejected(self):
        self.audio.write_bytes(self.audio.read_bytes()[:-10])
        with self.assertRaises(ValueError):
            analyze(self.audio, self.curves, 100)

    def test_cli_exit_codes(self):
        command = [sys.executable, str(Path(__file__).with_name("analyze_sync.py")),
                   "--audio", str(self.audio), "--curves", str(self.curves)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.write_curves([(0, 0), (0.35, 0.8)])
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.write_curves([])
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
