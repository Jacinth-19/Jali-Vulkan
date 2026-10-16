# M2 — connected local neural voice + human face

Status review: **2026-10-16**. The end-to-end prototype has passed actual Linux
CPU/browser execution on two newly entered sentences. This is not yet a packaged
Windows application, incremental streaming, or the richer native Vulkan renderer.

## What the user can do

Open the **Local neural face studio** preview, edit the script, and press
**Generate & play**. The application:

1. Validates bounded English text (1-500 characters).
2. Pauses/unloads the previous recording and returns the face to rest.
3. Creates a unique server session and runs the reviewed local Kokoro q8 CPU worker.
4. Uses the new WAV and its actual requested text as Rhubarb/PocketSphinx inputs.
5. Validates audio hash, duration, dialog/cue provenance and rig version.
6. Publishes a complete immutable session, never an intermediate speech result.
7. Downloads the WAV in the browser, verifies its SHA-256 and decoded duration,
   and plays it with the matching mouth cues on the audio media clock.

Most browsers allow playback following the form interaction. If autoplay policy
blocks it, the UI exposes a Play button; it does not report playing silently.
Generation finishes before playback: this is **whole-utterance generation**, not
incremental neural audio or interactive microphone conversation.

Users can pause, seek by audio controls or the colored cue strip, replay one of
the latest six performances in their tab, disable lip-sync, and adjust the manual
style/idle-motion/timing controls. Each selected recording has its own requested
script, session ID, downloadable WAV, cue JSON, and provenance record.

Stock voice is **Kokoro af_heart**, not earlier Arena voice-00 and not a clone.
eSpeak NG is a text phonemizer only; the waveform is produced by neural ONNX
inference. The browser face is the detailed CC0 MPFB/MakeHuman character, rendered
with Three.js/WebGL. The native eSpeak/Vulkan demo remains a separate path.

## Run on the tested Linux developer setup

Python 3.11, Node/npm and `gh` are needed for explicit setup. GitHub public source
access and PyPI/npm downloads are used; no speech API key is required.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/requirements-neural-studio.txt
npm ci --prefix tools
# Explicit model/runtime setup, not a hidden request-time download:
.venv/bin/python tools/prepare_kokoro_cpu.py
.venv/bin/python tools/build_neural_studio.py
# Long-running local development server:
.venv/bin/python tools/neural_studio_server.py --bind 0.0.0.0 --port 8082
```

Open the proxied port 8082 preview here, or `http://localhost:8082` on the machine
running the server. Browser requests use **relative URLs**; no client-side
localhost call is used to reach a different service. On an unencrypted remote
HTTP host, WebCrypto may not be available: use the HTTPS preview or localhost.

The builder explicitly prepares the head and pinned Linux Rhubarb executable,
retains license evidence, bundles the viewer and stamps model/retarget/bundle
hashes. The server checks installed Kokoro assets and built viewer/model hashes
before accepting requests. Requests do not install packages or download models.

**Windows backend is not verified/ported:** the current analyzer setup selects a
Linux binary, and the backend/process/package workflow needs a Windows pass. A
Windows browser can view this hosted preview; that does not establish a working
local Windows installation. Model-independent tests are separate from this setup.

## Protocol and provenance

- `GET /api/config`: per-run request token, limits, voice description and rig identity.
- `POST /api/generate`: only `{"text":"..."}`, JSON, <=8192 bytes, 1-500 characters.
  Same-origin browser policy and `X-Jali-Token` are checked. Returns a job ID (202),
  validation error (400), CSRF rejection (403), or busy response (409).
- `GET /api/jobs/<id>`: queued/synthesizing/analyzing, ready, or explicit error.
- `GET /sessions/<id>/{audio.wav,cues.json,requested-text.txt,manifest.json}`:
  published only after readiness. Byte-range audio requests are supported.

Session IDs are server-generated UUID hex strings. Clients cannot select output
paths, models, voices, reference recordings, commands or URLs. Static/media routes
are allowlisted. Model files, worker logs and incomplete sessions are not HTTP
endpoints; no directory listings are provided.

A ready session records:

- Original requested text and its UTF-8 hash. It is not labeled an independently
  verified transcription.
- Actual synthesized WAV hash, PCM properties, duration and measured signal levels.
- Local CPU model/stock voice hashes and provider identity.
- Rhubarb executable/archive hashes, actual audio hash and normalized dialog hash.
- Exact cue list, approximate recognition method, model/rig/retarget/viewer versions.
- Synthesis, analysis and total server pipeline wall times.

The backend rejects mismatches before publishing. The browser independently
verifies downloaded audio and session/rig association. These are consistency and
provenance checks, **not cryptographic proof of voice permissions or lip-sync quality**.

## Resource and failure behavior

- One generation job at a time, with no unbounded work queue. A second request gets 409.
- CPU-only ONNX inference, two intra-op threads, no GPU/cloud fallback.
- Speech subprocess timeout: 90 seconds. Analyzer timeout: 90 seconds.
- Worker waveforms are bounded to 60 seconds; large/invalid results fail.
- Browser polling is bounded; it shows an actionable failure rather than a fake performance.
- The latest six ready sessions are retained server-side per run; failures are bounded
  to six status records and their partial output is removed.
- Starting a new server run clears previous UUID session directories. Download any
  desired outputs first. This development retention policy is not durable user storage.
- Tabs keep up to six verified audio blobs for replay; older blobs are released.
  Another tab's jobs can expire server downloads earlier than a tab's local replay.
- Idle/paused static faces no longer redraw continuously. Orbit damping and audio
  playback still render as needed; this is not a frame-rate guarantee.
- Interrupting an in-progress model job/cancellation UI remains M6 work. This is
  not an incremental persistent model worker; each generation starts an isolated worker.

The token/origin checks protect against browser CSRF, **not remote authentication**.
Anyone with direct service access can obtain a token. This is a development server,
not a secure public hosting product. Bind to an appropriate interface for your own
setup, do not expose to untrusted users, and do not enter sensitive content. Local
session files contain requested text, audio, reports and worker diagnostics.

## Validation evidence

Fast tests (no neural weights, Node packages or GPU required for Python tests):

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/visemes.test.mjs
```

There are **63 Python tests and six JavaScript viseme tests** at this checkpoint.
HTTP tests use explicitly fake, model-free workers for rejection, concurrency,
retention and failure contracts. They are not counted as neural inference evidence.

Real integration, with the server running and assets prepared:

```sh
# Optional MP4 export captures the same solved new-text session and muxes its WAV:
EXPORT_VIDEO=1 node tools/smoke_neural_studio.cjs
```

The integration uses actual browser form clicks and two new CPU speech requests.
It checks downloaded hashes, actual closure morph weights, pause/seek, speech
reset, natural completion, history replay, mobile layout, and zero external
browser requests/console errors. Browser web security stays enabled.

See [the small retained evidence record](evidence/neural-studio-browser.json).
Full generated evidence lives in `artifacts/neural-studio/proof/`; audio, dialog,
cues and manifests live under `artifacts/neural-studio-sessions/<id>/` until
expiration/restart. The 15 fps MP4 is an **offline export**, not measured live FPS.
Software WebGL in this sandbox is slow; Windows/integrated-GPU performance is untested.
The same optimized GLB was decoded and validated: zero errors, nine retained warnings
(eight non-root skinned-mesh warnings and one generated tangent-space warning).

## Still open

- Listening and facial-quality review, including pronunciation, coarticulation and
  visible closures/rounding over the entire utterance (M1/M3).
- Better timing/retargeting and independent physical AV latency measurements (M3/M8).
- The original scripts are already known, but text+audio alone is not exact timing;
  no TTS phoneme durations or verified forced alignment are fabricated here.
- Native Vulkan support for this richer character (M4).
- Learned/controlled expressive behavior beyond procedural/manual styling (M5).
- Streaming, interruption and cancellation (M6).
- Local Windows verification, target-device profiling and a usable launcher (M7).
- Broader interchange, dependency/distribution/privacy review and release QA (M8).

M2's connected **prototype** is delivered; the overall project is not complete.

## M3 articulation and hosted CI

See [repeatable articulation review](neural-articulation.md) for the public
three-text corpus, short-cue/end-rest corrections, actual mesh review frames,
disposable CI runner, hosted resource inventory and remaining quality gates.
