# Jali-Vulkan

C++17 voice-to-face engine with **phoneme-driven live playback, imported GLB characters, and Vulkan compute morphing/skinning plus indexed rasterization**. The browser presents actual native-rendered frames on a Web Audio clock—not a pre-rendered movie or a JavaScript face simulation.

## Run the live demo here

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

A local Chatterbox provider entry point is available in `tools/authorized_voice.py`, with authorization/expiry/hash admission checks. **Neural inference is not installed, exercised, or connected to the preview here.** No human voice reference was supplied. Another voice's audio requires its own true alignment; eSpeak timings are not reused to fake alignment.

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

GitHub Actions runs the GCC/Clang matrix, sanitizers, and native software-Vulkan/browser checks on pushes, PRs, or manual dispatch. Native artifacts include actual runner resource inventory, validation logs, and screenshots; no GPU or neural inference is implied. See [CI resource details](docs/live-engine.md#github-actions-resource-and-validation-runs).

GCC/Clang sanitizer builds: add `-DJALI_ENABLE_SANITIZERS=ON`. Model-free and native tests remain separate; no credentials or voice models are used by CI.

## Documentation and layout

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
