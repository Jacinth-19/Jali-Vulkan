# Live engine: what changed and what still needs external inputs

## Implemented and runnable here

The default browser preview now uses **live native Vulkan frames**, not an MP4. The old offline exporter remains an explicit compatibility tool.

1. eSpeak NG produces PCM and timestamped **phoneme events** for the same synthesis call.
2. Phonemes map to independent `jawOpen`, `mouthRound`, and `mouthClose` controls. Bilabials (`m`, `b`, `p`) close the lips even though they may have acoustic energy; rounded vowels/approximants round the mouth. Short bounded coarticulation blends neighboring poses. This is a small English rule-based viseme mapper, not a learned facial solver.
3. A persistent C++ worker imports an actual **glTF 2.0 GLB** with vertices, indices, normals, colors, skin weights, joint hierarchy, inverse bind matrices, and named morph deltas.
4. A Vulkan **compute shader morphs then skins** every vertex. A compute-write → vertex-input-read barrier makes the output usable by the graphics pass. The graphics pipeline rasterizes indexed triangles into color/depth images, then copies the image into coherent host memory with transfer → host visibility and a completion fence.
5. The browser plays PCM through Web Audio. Its output-clock estimate drives on-demand native frame requests. The canvas displays JPEGs made from the Vulkan pixels; it does not reconstruct or animate character geometry in JavaScript.
6. Pause/seek restarts an `AudioBufferSource` at the correct sample offset and requests the corresponding native pose. There is at most one in-flight frame in the browser. Frames are not queued into an increasingly stale movie buffer.

The authored fixture contains **11,392 vertices, 20,736 triangles, two joints, and three morph targets**. It is generated as a real GLB at build time by `tools/make_character.py`, then parsed at runtime; the renderer does not bypass the importer with hardcoded geometry. No external human face assets are used.

**Speech synthesis remains whole-utterance before playback.** Frame delivery is live; incremental neural audio synthesis and microphone conversational input are not implemented. The short built-in eSpeak synthesis/mesh setup is measured separately as `prepare_seconds`, not advertised as a vendor latency guarantee.

## Run it

Sandbox (Linux x86_64 / Python 3.11):

```sh
python3 -m venv .venv
.venv/bin/python tools/bootstrap_sandbox.py
.venv/bin/python tools/preview_server.py --software-vulkan --port 8080
```

No MP4-generation step is required. Open the port 8080 preview and press play, or start a new live performance.

The live transport is currently tested on Linux/POSIX; Windows/macOS support has not been established.

Normal Linux machine: install the dependencies described in [running-demo.md](running-demo.md), plus a tinygltf **2.9.3** source checkout, including its `json.hpp`. Then:

```sh
cmake -S . -B build-live -DCMAKE_BUILD_TYPE=Release \
  -DJALI_ENABLE_ESPEAK=ON -DJALI_ENABLE_VULKAN=ON \
  -DTINYGLTF_INCLUDE_DIR=/path/to/tinygltf-2.9.3
cmake --build build-live --parallel
ctest --test-dir build-live --output-on-failure
.venv/bin/pip install -r tools/requirements-runtime.txt
.venv/bin/python tools/preview_server.py --port 8080
```

The bootstrap downloads and checksum-verifies tinygltf into the ignored dependency cache. It compiles four shaders and generates the GLB. No dependency source/binary or large rendered frame sequence is committed.

### Hardware selection

The renderer prefers discrete/integrated hardware devices with graphics + compute queues. It reports the actual selected device and a hardware/software classification. To **reject software fallback**, run:

```sh
.venv/bin/python tools/preview_server.py --require-hardware --port 8080
# Or invoke the native worker directly:
./build-live/jali_live --require-hardware --output artifacts/hardware-test
```

Do not combine this with `--software-vulkan`. In this sandbox the hardware-required path fails, as it should: there is no exposed hardware GPU. Software rendering cannot be transformed into hardware acceleration by changing a label. To validate hardware acceleration, run the same build on a Vulkan-capable host or GPU runner.

### Native worker protocol

`jali_live` accepts `--text`, `--output`, `--size`, `--asset /path/to/character.glb`, and `--require-hardware`. On startup it writes PCM, phoneme cues and metadata, then emits one JSON metadata line to stdout. Each subsequent finite audio-time line on stdin returns exactly `width*height*4` RGBA bytes. `quit` or stdin EOF terminates the worker.

`tools/live_session.py` owns this process, bounds startup/frame reads, serializes frames, and terminates it when replacing a session or closing the server. The HTTP layer admits one current live session and applies backpressure instead of building an unbounded request queue. Completed session data retention is five sessions for the live path. Failed setup directories are removed.

## Supported asset profile (not a universal glTF/FBX importer)

- Self-contained binary GLB, ≤16 MiB, one selected scene, one mesh instance/skin.
- Root-level identity mesh transform; all joint ancestors must be included in the skin.
- Up to 100,000 vertices, 600,000 indices, 128 joints (256-node import bound), and four influences per vertex.
- Triangle primitives with float position/normal and RGB vertex color, joint indices and weights.
- A named `Jaw`/`jaw` bone and exactly three named morph targets: `jawOpen`, `mouthRound`, `mouthClose`. Their names, not assumed source indices, define the mapping.
- Zero default morph weights and finite, rigid joint matrices and inverse binds. Nonuniform scale/shear is rejected instead of producing incorrect normals.
- No textures/materials, authored animation tracks, sparse accessors, compression/required extensions, or external-file references in this first adapter. Unsupported content fails explicitly.

The four-influence limit is still an engine policy, not a glTF specification limit. Assimp/FBX support, general authoring rigs, and unrestricted glTF scene semantics remain separate integrations.

## Measurement and regression gates

Locally executed:

- Actual PCM + phoneme event capture and independent bilabial/vowel/rounding mappings.
- Same-time pose interpolation and explicit pause/rest behavior.
- GPU/CPU comparison for **all imported vertices** under three distinct poses, tolerance `2e-5` per position component.
- Distinct neutral/rounded/closed-mouth rasterized images and deterministic repeated poses.
- Eleven malformed-GLB rejection cases: hierarchy cycles, huge transforms, scale, bounds, wrong target names, external URI, duplicate joints, missing weights, bad joint index, unnormalized weights, and nonfinite positions.
- Official Khronos glTF Validator: **zero errors, warnings, infos, or hints** for the authored GLB.
- Browser checks: Web Audio progression, live frame requests, new phoneme sessions, pause, seek, mobile overflow, and **no MP4 requests**.
- HTTP/admission unit tests, including bad frame times, expired sessions, backpressure, cross-origin submission rejection, and cloning grant failure paths.

The UI's **pose/audio offset** is an estimate comparing the requested pose timestamp with the browser's audio output-clock estimate when the returned frame is drawn. It is not a camera/loopback measurement or certified physical display/speaker synchronization. Network RTT affects delivered frame rate. Lookahead is bounded to 100 ms, one frame request is in flight, and excessive offsets are visibly highlighted rather than passed as zero. Real target-device p95 latency/throughput still needs profiling.

The shader still uses host-visible coherent buffers and synchronous readback. Those are correctness-first choices, not optimal discrete-GPU memory/throughput design. Vulkan validation layers are not installed locally; no local validation-layer-clean or hardware-GPU run is claimed.

## Neural voice cloning: adapter exists, assets are still required

There is **no authorized real speaker reference or reviewed Chatterbox checkpoint bundle for the cloning adapter**. A separate stock-voice Kokoro CPU experiment now works; see [local-neural-speech.md](local-neural-speech.md). This sandbox's network allowlist also does not permit the default Hugging Face model downloads. The preview therefore stays on the disclosed built-in eSpeak voice, not a fake clone or hidden cloud fallback.

`tools/authorized_voice.py` adds an opt-in **local Chatterbox adapter** using `ChatterboxTTS.from_local(...)` and `generate(..., audio_prompt_path=...)`, based on the inspected [upstream API](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/tts.py). It is a separate operator CLI, **not enabled in the web API**.

Before importing the neural runtime it checks:

- Active, unexpired, timezone-aware voice authorization with `local-voice-synthesis` scope and nonempty consent/subject IDs.
- A SHA-256-matched, 3–30 second mono PCM16 reference WAV at 16–48 kHz.
- Explicit checkpoint-license review acknowledgment and hashes for `ve.safetensors`, `t3_cfg.safetensors`, `s3gen.safetensors`, and `tokenizer.json`.
- No optional pickled `conds.pt`; the approved recording supplies the conditioning.
- Offline Hugging Face/Transformers mode and no call to `from_pretrained`.
- An explicit error if CUDA is requested but absent, with no hidden CPU fallback.
- A second grant/reference/model check before committing output, then bounded PCM and synthetic provenance output. Upstream watermarking is not removed, but its detection is not independently verified.

A manifest is an operator admission record, **not cryptographic proof of consent or legal clearance**. The operator must verify the underlying permission/license, secure the files/runtime, and enforce revocation/retention. Offline environment variables are not a network-security sandbox for arbitrary third-party model code.

Create a real private manifest outside Git with this schema (all capitalized placeholders must be replaced with reviewed actual values):

```json
{
  "schema": 1,
  "consent_id": "YOUR_DOCUMENTED_CONSENT_ID",
  "subject_id": "YOUR_AUTHORIZED_SUBJECT_ID",
  "status": "active",
  "scopes": ["local-voice-synthesis"],
  "expires_at": "YOUR_AGREED_EXPIRY_WITH_TIMEZONE",
  "reference": {"path": "reference.wav", "sha256": "REAL_REFERENCE_SHA256"},
  "model": {
    "directory": "model",
    "license_reviewed": true,
    "sha256": {
      "ve.safetensors": "REAL_SHA256",
      "t3_cfg.safetensors": "REAL_SHA256",
      "s3gen.safetensors": "REAL_SHA256",
      "tokenizer.json": "REAL_SHA256"
    }
  }
}
```

With the reviewed Chatterbox runtime/dependencies installed separately:

```sh
python tools/authorized_voice.py --manifest /private/voice/grant.json \
  --text "This recording is synthetic." --output /private/output/speech.wav --device cuda
```

**Actual Chatterbox inference is not tested here**, and additional submodel artifacts may be needed by the chosen runtime. The admission tests deliberately use dummy files without loading a model; they do not validate checkpoint quality or license rights.

The resulting neural audio is **not automatically paired with eSpeak timings**: those would be wrong for another voice's timing. A neural/audio forced-alignment adapter with its own licensed local weights is still needed before this provider can join the phoneme-aligned live preview. No fake retiming or RMS fallback is labeled phoneme alignment.

### Inputs needed to finish the remaining limitations

1. A hardware Vulkan host/runner for genuine hardware validation and performance profiling.
2. A voice recording you are authorized to clone, its documented scope/expiry, and a licensed local checkpoint/runtime bundle.
3. A licensed local forced-aligner model (or a speech provider that returns true timings) for that generated audio.

Until those are supplied, hardware acceleration and an end-to-end neural clone in the live preview remain **blocked**, not “fixed” by configuration alone.

## GitHub Actions resource and validation runs

`.github/workflows/ci.yml` runs on branch pushes, pull requests, and manual dispatch:

- GCC and Clang, each in Debug and Release, plus CPU ASan/UBSan checks.
- A native Linux build using system eSpeak, Mesa **software** Vulkan, and the
  Khronos validation layer. Validation diagnostics fail the job.
- Official glTF validation, actual native-worker PCM/phoneme/frame checks, the
  legacy native CLI, and hardware-required rejection of software devices.
- Headless Chromium audio-clock, generation, pause/seek, playback-end, and mobile
  layout checks. The disposable preview and native worker are stopped afterward.

The native job records its actual CPU/RAM/disk and Vulkan device inventory. It
uploads built-in synthetic speech, screenshots, metadata, and test logs as
`native-backend-evidence`, retained for three days. CPU matrix jobs retain their
synthetic fixture evidence for three days. No real recordings, neural checkpoints,
private grants, secrets, or model training are part of this workflow. Artifacts in
this public repository must be treated as public evidence.

Standard hosted CPU jobs do not establish hardware-GPU performance or neural
voice quality. A paid/larger/GPU runner must be explicitly provisioned and
approved separately. Do not send untrusted PR code or private voice assets to a
persistent self-hosted GPU runner. The repository's Actions permissions, quotas,
and any required approvals still govern whether jobs can start. Actions are
finite tests, not an always-on deployment of the live preview.

The 128-joint palette uses an 8,208-byte C++/GLSL pose ABI. Weighted 67/128-joint
fixtures exercise joints above the former 64-joint limit against the CPU
reference. This does not add rich MPFB multi-mesh/material/morph support; see
[implementation scope](performance-controls.md).
