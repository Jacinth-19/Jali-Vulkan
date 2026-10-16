# M1: local stock neural speech — CPU smoke test

Reviewed/tested: **2026-10-16**, Linux x86_64, Python 3.11.2.

## Result

We successfully generated **two previously unused sentences locally**, using
Kokoro-82M v1.0 q8 with ONNX Runtime's **CPUExecutionProvider only** and the stock
`af_heart` voice. No hosted speech API or cloned speaker reference was used.
This voice is **not** the earlier Arena `voice-00`.

| Item | Observed result |
|---|---|
| Engine load, after dependency imports | 0.798 seconds |
| Dependency import | 0.345 seconds |
| First sentence | 8.832 s audio generated in 3.642 s; RTF 0.4124 |
| Second sentence, same loaded engine | 6.997 s audio generated in 3.438 s; RTF 0.4914 |
| Peak process RSS | 440.53 MiB, including dependencies and model |
| Inference threads | 2 intra-op, 1 inter-op |
| Output | 24 kHz mono PCM16 WAV |
| Clipped samples | 0 in both tested waveforms |
| ONNX model | 92,361,116 bytes, plus 522,240-byte stock style tensor |

These are single-run sandbox observations, not averages, p95 results, or Windows
laptop measurements. The first synthesis includes initial phonemization/runtime
work. Neither audio generation time nor the offline demo video proves live face
rendering FPS. Waveform checks do **not** establish intelligibility/naturalness;
listening review remains open.

The small machine-readable record is retained in
[evidence/local-neural-cpu-smoke.json](evidence/local-neural-cpu-smoke.json).
Generated WAVs, exact requested text, and a manifest are written to
`artifacts/local-neural-speech/`, outside Git.

## What text plus audio gives us

For a TTS-generated sentence, we already know its requested text. We keep that
text paired with the resulting audio and hash; we do not need to call speech
recognition just to recover our own script. However, requested text is not an
independently checked transcription: synthesis may omit or mispronounce content.
Listen and correct the alignment transcript if necessary.

The original JALI-style text/audio input distinction still matters:

1. Text helps identify the intended words/sounds.
2. The actual audio determines when those sounds occurred and provides prosody.
3. An alignment/duration stage supplies usable times.
4. Rig-specific retargeting turns those events into facial motion.

**Having text and audio does not by itself produce verified phoneme timestamps.**
Our existing Rhubarb path uses both to estimate nine mouth classes. This particular
Kokoro ONNX export returns a waveform only; we do not invent timing from its G2P
token list. A timestamp-capable TTS export is another future option, but its times
would still need verification and adjustment for trimming/chunking.

## Reproduce

Use an isolated Python 3.11 environment on the tested Linux setup:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/requirements-local-neural.lock.txt
# Explicit network/setup step, separate from synthesis:
.venv/bin/python tools/prepare_kokoro_cpu.py
# Two new test sentences; no model/voice downloads or hosted speech calls:
.venv/bin/python tools/local_neural_speech.py
# Or bounded new text:
.venv/bin/python tools/local_neural_speech.py \
  --text "Today we are testing a completely new sentence." \
  --output artifacts/my-new-sentence --threads 2
```

The setup extracts exact data/notice members; it does not run npm hooks or the
JavaScript packages. It verifies archive SHA-512 integrity, the joined model
SHA-256, and the raw voice SHA-256. Synthesis rechecks the two asset hashes before
importing the inference runtime. There is no cloud/eSpeak-audio fallback.

Python dependencies are separately pinned in
`tools/requirements-local-neural.lock.txt`. They were resolved and executed on
Linux/Python 3.11 originally, and subsequently installed/executed on a fresh
hosted Windows x64/Python 3.11 runner. This is not a clean consumer Windows
installation or target-laptop test; see [Windows results](windows-neural-studio.md).
No GPU extras are installed. The observed Linux environment was about 242 MiB;
allow at least 1 GB of free disk for dependencies, temporary downloads, caches and
model data (platform and pip-cache usage vary). The two setup archives are about
61 MiB and 26 MiB, separate from the extracted model.

The generator caps requests at 500 characters, speed 0.5-2.0 and 1-8 intra-op
threads; it checks style-table bounds and finite, non-silent waveforms. Oversized
or invalid inputs fail rather than becoming an apparently passing performance.
It is an operator CLI experiment, not an authenticated/public TTS service.

## Artifact provenance and licenses

- Original model family/code: https://github.com/hexgrad/kokoro (Apache-2.0).
- Model/export origin: `onnx-community/Kokoro-82M-v1.0-ONNX`.
- Reviewed model redistribution: npm `kokoro-q8-shards@1.0.0`; its README explicitly
  identifies the model, Apache-2.0 terms and joined-file hash.
- Stock tensor: original `kokoro-js@1.2.1` npm package, under its Apache-2.0 license.
- Model SHA-256: `fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478`.
- Voice SHA-256: `d583ccff3cdca2f7fae535cb998ac07e9fcb90f09737b9a41fa2734ec44a8f0b`.
- Adapter dependency: `kokoro-onnx==0.4.9` (MIT project).
- eSpeak NG/phonemizer-fork is used for **text phonemization**, not waveform synthesis.
  Those components have GPL obligations; do not call this stack entirely MIT/Apache.
  Review exact binary/source obligations before distributing a bundled runtime.
- ONNX Runtime, NumPy and transitive dependencies retain their own terms; the M8
  full dependency/distribution review remains open.

The sandbox cannot reach the standard Hugging Face download host. A GitHub
release download also redirected to a blocked release-assets host. We therefore
used the stated npm model redistribution and the original npm voice package, not
an undeclared proxy. We checked the official GitHub Apache-2.0 license and package
license/redistribution evidence. The Hugging Face model card and an independent
upstream byte comparison were **not** directly fetched here; no broader audit of
training-data permissions is claimed.

Full archive integrity strings and extracted notices are kept by setup under
`models/kokoro/provenance.json` and `models/kokoro/licenses/`. Checkpoints and
model download archives remain ignored, never shipped in source or public CI.

## Implementation detail

The available export has `input_ids:int64`, `style:float32`, `speed:float32` and a
`[1,N]` waveform output. The pinned wrapper's default handling of this export
uses the wrong speed dtype and assumes a flat waveform. Our small explicit
adapter fixes those two schema differences, uses a CPU-only session with bounded
threads, and otherwise reuses the package's phonemization/chunking/trim path.
No untrusted pickled speaker conditioning is loaded: the temporary NPZ is created
locally from the verified, finite float tensor, and NumPy's pickle loading remains off.

## Remaining

- Listen to the samples and review pronunciation/naturalness.
- Broader unseen-text testing, repeated-run measurements and dependency review.
- Connected in the separate M2 studio; the standalone CLI remains audio-only.
- Upgrade/validate articulation and alignment as needed (M3).
- Test and measure the actual Windows/i5 U-series/16 GB device (M7).
- Personal cloning, real incremental streaming and emotion solving are not delivered here.

This proves **local stock neural synthesis**, not completion of the full Jali system.

**Follow-up, 2026-10-16:** M2 now connects new speech to actual-audio analysis and
the human viewer; see [the connected studio](neural-studio.md). The M1 sample
manifest remains an immutable record of the earlier standalone checkpoint.
