# Build dependencies and optional offline export

**The default preview now uses live phoneme-driven GPU skinning.** See [live-engine.md](live-engine.md) for current behavior, run commands, hardware enforcement, GLB restrictions, and blocked neural-provider requirements. This page covers installation details and the retained offline export tool.

## Platform dependencies

Normal developer machines should use maintained platform Vulkan headers/loader/drivers, eSpeak NG development files/data, and `glslangValidator`. Typical Debian/Ubuntu packages are:

- `libvulkan-dev`
- `mesa-vulkan-drivers` (software Vulkan when needed)
- `libespeak-ng-dev`
- `glslang-tools`

The imported-mesh backend additionally requires a **tinygltf 2.9.3 source checkout including `json.hpp`**, supplied with `-DTINYGLTF_INCLUDE_DIR=/path/to/checkout`. The sandbox bootstrap fetches and SHA-256-verifies this source revision. No dependency download runs automatically during CMake configuration.

CMake options:

- `JALI_ENABLE_ESPEAK=ON`: build the real C++ eSpeak PCM/phoneme provider.
- `JALI_ENABLE_VULKAN=ON`: build native rendering, GLB loader and original asset generation; Python is required for the asset generator.
- `JALI_ENABLE_SANITIZERS=ON`: GCC/Clang address + undefined-behavior instrumentation.

Nonstandard locations can be supplied with `ESPEAK_INCLUDE_DIR`, `ESPEAK_LIBRARY`, `Vulkan_INCLUDE_DIR`, and `Vulkan_LIBRARY`. `JALI_ESPEAK_DATA` points to the **parent directory containing `espeak-ng-data`**. `VK_ICD_FILENAMES` selects a specific Vulkan ICD. Standard discovery prefers compatible discrete/integrated devices over CPU devices; the explicit hardware-required mode rejects a CPU fallback.

If `glslangValidator` is absent, `npm ci --prefix tools --ignore-scripts` supplies the pinned `@webgpu/glslang` build-time WASM compiler. Native rendering does not use Node, WASM, a browser GPU renderer, or a JavaScript reconstruction of the face.

Install optional preview/encoding packages in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements-runtime.txt
```

Pillow compresses live native frames to JPEG. `imageio-ffmpeg` is needed only for offline MP4 export.

## Sandbox fallback

```sh
python3 -m venv .venv
.venv/bin/python tools/bootstrap_sandbox.py
```

This opt-in helper supports Linux x86_64 / Python 3.11. It installs pinned CMake/Python tooling, runs npm's lockfile-based dependency install, and retrieves checksum-verified Vulkan Headers 1.3.290, eSpeak NG 1.51 headers, tinygltf 2.9.3, and the Linux CPython 3.11 `piper-phonemize` 1.1.0 wheel. Only the wheel's eSpeak library/data is used; no Piper voice model is downloaded.

It extracts the Vulkan loader and SwiftShader runtime from the pinned `@sparticuz/chromium` package. It does not launch Chromium for synthesis/rendering. The browser binary is used **only** by the separately invoked browser smoke test.

All downloaded sources/binaries, compiled shaders, generated GLB assets and build products live in ignored directories. Bootstrap makes network calls; normal built-in synthesis/rendering is local afterward. These pinned development binaries are not a production Vulkan SDK or a completed supply-chain review.

Caches/build directories may not survive a sandbox snapshot. Rerun bootstrap to recreate them; source files and run instructions remain in the repository.

## Legacy offline fixture/export path

This remains useful for reproducible artifacts and comparisons, but is no longer the default browser path.

```sh
./build-live/jali_demo --voice espeak --renderer vulkan \
  --text "Hello from the offline compatibility path." \
  --size 512 --fps 24 --output artifacts/offline

.venv/bin/python tools/render_session.py --software-vulkan \
  --text "Hello from Jali." --output artifacts/offline
```

The legacy `jali_demo` Vulkan renderer is the analytic procedural head with envelope-driven jaw motion. The newer `jali_live` path imports a GLB and uses true phoneme events plus GPU morph/skin/raster passes. These are deliberately distinct capabilities; the old exporter is not mislabeled a skinned mesh or neural clone.

Offline output includes PCM16 `session.wav`, envelope `face.csv`, curve-onset `metrics.json`, `session.json`, and native `frames.rgba`. The Python exporter adds MP4/poster/timing metadata and deletes raw frames. Its curve-onset result is a software smoke test, not a rendered lip-sync quality score.

The CPU baseline still defaults to mock tones/headless curves:

```sh
./build/jali_demo --output artifacts/demo
python3 tests/analyze_sync.py --audio artifacts/demo/session.wav \
  --curves artifacts/demo/face.csv --max-lag-ms 100
```

Analyzer exit codes are 0 pass, 1 measured threshold failure, 2 invalid/inconclusive input. Silence/missing mouth activity cannot pass automatically.

## Tests and licensing

Current live test details and limits are in [live-engine.md](live-engine.md). `node tools/smoke_preview.cjs` checks an already-running port 8080 preview, including live frame requests, Web Audio, pause/seek and mobile layout. It uses sandbox-disabling flags for the test browser; do not use that launch setup for untrusted browsing or production.

Before distribution:

- eSpeak NG is **GPL-3.0-or-later**; linking/distributing the executable requires compatible licensing and obligation review. A Piper wrapper's license does not replace eSpeak's license.
- tinygltf is MIT; preserve its notices and review its JSON/parser dependencies. Original GLB fixture geometry is authored by this repository's generator, not downloaded face artwork.
- Vulkan Headers/Loader, SwiftShader and glslang retain their component-specific upstream terms. The npm wrapper's label is not a license for every bundled binary.
- `imageio-ffmpeg`'s Python wrapper license does not determine its FFmpeg/libx264 binary licensing. Inspect the GPL-enabled build configuration and preserve applicable notices before shipping.
- Chromium/NSS test binaries have their own multi-component terms and are not required by the normal native renderer.
- Neural checkpoints, training data, reference recordings and generated output rights need separate review from model code. The local neural adapter is not exercised without an approved bundle.

No owner-selected project distribution license has been added on the user's behalf.
