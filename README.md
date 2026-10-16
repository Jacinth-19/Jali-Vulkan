# Jali-Vulkan

C++17 voice-to-face engine with **phoneme-driven live playback, imported GLB characters, and Vulkan compute morphing/skinning plus indexed rasterization**. The browser presents actual native-rendered frames on a Web Audio clock—not a pre-rendered movie or a JavaScript face simulation.

## Run the native live demo here

Linux x86_64 / Python 3.11 sandbox:

```sh
python3 -m venv .venv
.venv/bin/python tools/bootstrap_sandbox.py
.venv/bin/python tools/preview_server.py --software-vulkan --port 8080
```

Open the port 8080 preview and press play, or enter text and select **Start live performance**. No video-encoding step is needed. The sandbox has no exposed hardware GPU: the UI truthfully reports **SwiftShader software Vulkan**.

On a hardware Vulkan machine, omit `--software-vulkan`. Use `--require-hardware` to reject software fallback. See [the live engine guide](docs/live-engine.md) for standard build instructions and remaining external requirements.

## Current capabilities

| Working and tested | Still blocked or outside scope |
|---|---|
| Real built-in eSpeak speech and phoneme timing events | Neural cloning needs an authorized reference and reviewed local weights |
| Lip closure, jaw opening, rounding, and short coarticulation | Learned facial solving / broader language-specific viseme sets |
| Imported GLB: 11,392 vertices, two joints, three named morph targets | General FBX/Assimp/DCC rig compatibility and unrestricted glTF |
| GPU morph-then-skin compute pass + rasterized triangles | Hardware-GPU validation in this CPU-only sandbox |
| Persistent native renderer, Web Audio clock, live frame requests, pause/seek | Incremental neural audio inference and microphone conversation |
| CPU/GPU deformation comparison, malformed-asset tests, official glTF validation | Physical display/speaker sync certification and target-device p95 budgets |

A local Chatterbox provider entry point is available in `tools/authorized_voice.py`, with authorization/expiry/hash admission checks. **Chatterbox cloning inference is not installed, exercised, or connected to the preview here.** A separate local stock-voice Kokoro CPU experiment has now succeeded; see below. No human voice reference was supplied. Another voice's audio requires its own true alignment; eSpeak timings are not reused to fake alignment.

## Local stock neural speech — CPU checkpoint passed

Kokoro-82M v1.0 q8 now generates new speech locally with ONNX Runtime's CPU
provider, using the stock `af_heart` voice. Two new 24 kHz PCM16 WAVs were produced
and validated. This is not Arena `voice-00` or a clone. The new connected studio
now pairs newly generated audio with its own mouth cues and the human face. eSpeak NG supplies phonemization only; the waveform comes
from the neural ONNX model.

See [setup, measured results and license/provenance limits](docs/local-neural-speech.md)
and the [updated project tracker](docs/project-tracker.md). Use explicit model
setup followed by `tools/local_neural_speech.py`; generation has no hosted speech
fallback. The target Windows laptop has not been benchmarked.

## Connected neural face studio — M2 prototype delivered

**New text → local Kokoro CPU speech → analyze that WAV with its script → human
WebGL face**, through one Generate & play action. No prerecorded speech or earlier
recording's timing is substituted. Each session carries audio/text hashes, cue
provenance and a versioned rig identity; the browser also verifies the WAV hash.

See [setup, protocol, evidence and limitations](docs/neural-studio.md).
After explicit model/dependency setup:

```sh
.venv/bin/python tools/build_neural_studio.py
.venv/bin/python tools/neural_studio_server.py --bind 0.0.0.0 --port 8082
```

The port 8082 preview offers new generation, play/pause/seek, six-session history,
WAV/cue/manifest downloads and manual expression controls. The Linux CPU/browser
pipeline passed two real form submissions plus fast contract tests. It completes
whole utterances before playback, uses estimated visemes, and does not claim
learned emotion, native support for this rig, or tested target-laptop performance.
This is a development service, not authenticated public hosting; do not enter
sensitive content. The Windows x64 developer backend now passed real CPU speech,
Windows audio analysis and live Chrome integration in [nine-job Actions run 38843451199](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38843451199).
See [Windows developer setup and actual measurements](docs/windows-neural-studio.md).
A standalone installer and target-laptop validation remain open.

## Personal face and voice test assets

A downloadable CPU-first test pack is described in [test-pack.md](docs/test-pack.md).
It combines our original rigged GLB, a standalone offline-capable rig inspector,
three externally generated stock neural-voice references, and a separate actual
local eSpeak/Vulkan timing-baseline video. That earlier pack keeps the neural recordings separate from its manual rig
inspector; it remains available unchanged. Neither pack is a self-hosted neural
clone demonstration. Generated media stays under ignored `artifacts/`.

## Detailed human face driven by the existing clips (WebGL)

The new `web/neural-head/` viewer uses the **same three stock neural WAVs** to
animate a textured **CC0 MPFB/MakeHuman avatar**: 67 bones, 66 main-mesh face
controls, and matching teeth/tongue targets. CPU Rhubarb analyzes the actual WAVs
with their dialog; nine estimated mouth classes are retargeted with short
coarticulation. This is **approximate automatic viseme timing, not manually
verified phoneme forced alignment** or learned emotional facial solving.

The delivered ZIP opens offline by double-clicking `index.html`; a portable
H.264/AAC lip-closure example is included. No neural model or server is needed
to play it. See [the human-head guide](docs/human-head-demo.txt) for provenance,
license evidence, limitations and Windows playback instructions.

**This viewer uses Three.js/WebGL, separately from the native Vulkan demo.**
The strict native importer does not yet support this richer character. Target
Windows laptop speed has not been measured; software browser rendering here is
slow, so the 15 fps example video is rendered offline rather than a live-FPS claim.

Rebuild/test on the Linux developer setup after `npm ci --prefix tools` and
installing Pillow/imageio-ffmpeg in `.venv` (existing WAVs must be present):

```sh
.venv/bin/python tools/build_neural_head.py
.venv/bin/python -m http.server 8081 --bind 0.0.0.0 --directory artifacts/neural-head-demo
# In another terminal; exports the real clip-driven face as well as testing it:
EXPORT_VIDEO=1 node tools/smoke_neural_head.cjs
.venv/bin/python tools/build_neural_head.py --seal-only
# Fast tests, no downloaded character/recognizer or GPU needed:
node --test tests/visemes.test.mjs
python3 -m unittest discover -s tests
```

The build pins/verifies the source model and Rhubarb repack hashes, records each
recording's hash, retains explicit upstream per-model CC0 evidence, and validates
both compressed-container structure and decoded geometry. The official validator
reports zero errors and nine retained warnings on decoded geometry. Runtime
pruning reduces shader work to 20 used controls without deleting other controls
from the downloadable GLB. Rebuilding the analyzer does not regenerate speech.

## Build/test without native dependencies

CMake 3.16+, C++17 with `std::filesystem`, and Python 3.8+:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

This default path needs no third-party C++ libraries or Python packages. It tests deterministic mock audio/curves, rig contracts, phoneme mapping, HTTP contracts, and neural-provider admission rules without loading a neural model. On multi-configuration generators, use `--config Debug` and CTest `-C Debug`.

Optional native build (system Vulkan/eSpeak development files and tinygltf 2.9.3 checkout):

```sh
cmake -S . -B build-live -DCMAKE_BUILD_TYPE=Release \
  -DJALI_ENABLE_ESPEAK=ON -DJALI_ENABLE_VULKAN=ON \
  -DTINYGLTF_INCLUDE_DIR=/path/to/tinygltf-2.9.3
cmake --build build-live --parallel
ctest --test-dir build-live --output-on-failure
```

`glslangValidator` compiles the shaders. If it is unavailable, `npm ci --prefix tools` provides the pinned WASM shader compiler. It also provides the official glTF Validator and optional browser test tools.

GitHub Actions runs the GCC/Clang matrix, sanitizers, and native software-Vulkan/browser checks on pushes, PRs, or manual dispatch. Native artifacts include actual runner resource inventory, validation logs, and screenshots; software Vulkan is not hardware-GPU validation. A separate neural-studio job now runs actual Kokoro CPU inference, generated-WAV/dialog analysis and detailed-face browser review on this session branch or manual dispatch. [Hosted neural results and M3 scope](docs/neural-articulation.md) include the successful seven-job run and remaining quality gates. See [CI resource details](docs/live-engine.md#github-actions-resource-and-validation-runs).

GCC/Clang sanitizer builds: add `-DJALI_ENABLE_SANITIZERS=ON`. Model-free and native tests remain separate; no credentials or voice models are used by CI.

## Documentation and layout

- **[Project tracker — completed work, remaining tasks and acceptance gates](docs/project-tracker.md)** — the ongoing eight-workstream checklist and agreed execution order.
- **[Live engine and remaining requirements](docs/live-engine.md)** — current architecture, supported GLB profile, hardware enforcement, measurements, neural adapter, and authorization schema.
- [Build dependencies and offline export](docs/running-demo.md) — platform packages, optional MP4 compatibility tool, licensing.
- [Architecture and milestones](docs/architecture.md) — original CPU baseline and larger engine roadmap.
- [Technical review](docs/technical-review.md) — source-backed corrections to the original report.

```text
include/jali/              Voice, phoneme, rig, character, renderer and QA contracts
src/                       CPU pipeline, eSpeak, GLB importer, Vulkan, CLI/live worker
shaders/                   GPU morph/skin, mesh rasterization, legacy analytic face
tools/make_character.py    Original GLB fixture authoring (no external face art)
tools/live_session.py      Bounded persistent native frame transport
web/                       Web Audio + native-frame presentation controls
tests/                     Contracts, malformed assets, GPU/CPU and HTTP tests
.github/workflows/ci.yml    CPU/sanitizer builds and native software-Vulkan checks
```

## Safety and distribution

The default preview uses only the disclosed built-in English synthetic voice. It has no public voice-upload/cloning endpoint. The private neural-provider CLI requires a reviewed grant/reference/model bundle; its manifest is not proof of legal consent. No commercial voices or human identities are silently substituted.

The preview is a **development server**, not an authenticated production service. It stores submitted text/audio locally, limits requests and retains bounded sessions; do not enter sensitive content. Generated media, binaries, models and datasets are ignored by Git. Third-party model code requires separate isolation and supply-chain review.

Optional eSpeak is GPL-3.0-or-later. tinygltf and all runtime/compiler/media dependencies retain their own licenses; wrapper package labels do not relicense bundled components. Review linked-executable obligations before distribution. This repository still has no owner-selected distribution license.

### Early Windows-browser checkpoint

The offline playback pack adds half-speed articulation review, per-recording notes
and explicit JSON export of visible-tab render observations. It requires no Python
or speech-model installation for playback. See [extraction and review instructions](docs/windows-playback-checkpoint.txt)
and [the eight-job Linux/Windows validation and remaining scope](docs/playback-checkpoint.md).
This is not a port of the local speech backend, a native Vulkan package, or a
performance claim for your Windows laptop.

### Generate new speech on Windows x64

With Python 3.11 x64, Node 22 and GitHub CLI public-source access installed, run
`windows/setup-neural.ps1` once, then `windows/start-neural.ps1`. Open the localhost
URL printed by the launcher. Setup is explicit/networked; generation is local CPU
with no hosted-speech fallback. These are developer scripts, not a standalone
installer. [Prerequisites, results and remaining limitations](docs/windows-neural-studio.md).

### One-command Windows benchmark

After explicit Windows setup, run `windows/benchmark.ps1`. It generates six new
public test recordings by default and writes model/import/generation/analysis
times, peak worker memory and visible-browser rendering observations to
`artifacts/jali-benchmark-report.json`. Nothing uploads automatically; inspect the
report before sharing. Independent-reference templates and a static native-rig
gap audit are included, not a completed quality score or Vulkan port.
[Commands, actual Windows CI evidence and remaining M3/M4 work](docs/windows-benchmark.md).
