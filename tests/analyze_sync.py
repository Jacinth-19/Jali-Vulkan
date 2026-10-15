#!/usr/bin/env python3
"""Offline onset-only contract check. Not a video/lip-reading quality metric."""
import argparse
import csv
import json
import math
from pathlib import Path
import struct
import sys
import wave


def analyze(audio_path, curves_path, max_lag_ms):
    if not math.isfinite(max_lag_ms) or max_lag_ms < 0:
        raise ValueError("lag tolerance must be finite and nonnegative")
    with wave.open(str(audio_path), "rb") as audio:
        rate = audio.getframerate()
        count = audio.getnframes()
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("expected uncompressed mono PCM16 WAV")
        if not 100 <= rate <= 192000 or count == 0:
            raise ValueError("empty audio or unsupported sample rate")
        raw = audio.readframes(count)
        if len(raw) != count * 2:
            raise ValueError("truncated audio")
    samples = [value[0] / 32768 for value in struct.iter_unpack("<h", raw)]
    window = max(1, rate // 100)
    audio_onset = None
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        energy = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        if energy > 0.05:
            audio_onset = start / rate
            break
    face_onset = None
    previous = -1.0
    rows = 0
    with Path(curves_path).open(newline="", encoding="utf-8") as curves:
        reader = csv.DictReader(curves)
        if reader.fieldnames != ["audio_time_seconds", "jaw_open"]:
            raise ValueError("unexpected curve schema")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("malformed curve row")
            timestamp, jaw = float(row["audio_time_seconds"]), float(row["jaw_open"])
            if not math.isfinite(timestamp) or timestamp < 0 or timestamp <= previous or timestamp >= count / rate:
                raise ValueError("invalid, unordered, or out-of-duration timestamp")
            if not math.isfinite(jaw) or not 0 <= jaw <= 1:
                raise ValueError("invalid jaw weight")
            if face_onset is None and jaw > 0.1:
                face_onset = timestamp
            previous = timestamp
            rows += 1
    if not rows or audio_onset is None or face_onset is None:
        raise ValueError("inconclusive sync: missing audio or mouth activity")
    lag = (face_onset - audio_onset) * 1000
    return {"measurement": "curve_onset_only", "audio_onset_seconds": audio_onset,
            "face_onset_seconds": face_onset, "signed_lag_ms": lag,
            "passed": abs(lag) <= max_lag_ms + 1e-9}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--curves", type=Path, required=True)
    parser.add_argument("--max-lag-ms", type=float, default=100)
    args = parser.parse_args()
    try:
        result = analyze(args.audio, args.curves, args.max_lag_ms)
    except (ValueError, OSError, wave.Error, EOFError, struct.error) as error:
        print(f"sync analyzer: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
