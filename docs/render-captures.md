# Actual README renderer images

The four PNGs in [`images/`](images/) are **actual application renderer output**,
not generated concept art. [`render-evidence.json`](images/render-evidence.json)
records their SHA-256 hashes, source-file hashes, exact audio hashes, sampled
speech times and renderer identities. They are point-in-time captures, not a
claim that future source revisions produce byte-identical pixels on every GPU.

| Image | Actual source |
|---|---|
| `webgl-closure.png` | Detailed MPFB head, estimated Rhubarb A / P-B-M cue |
| `webgl-contact.png` | Same WebGL rig, estimated G / F-V cue |
| `webgl-rounding.png` | Same WebGL rig, estimated F / OO-W cue |
| `native-vulkan.png` | Original authored Jali android with the 67-joint **test** skeleton, native Vulkan compute + raster readback |

The WebGL captures use three new Kokoro CPU recordings of the public test corpus,
with each exact WAV analyzed alongside its requested text. Cosmetic motion is
disabled and styling is neutral. Poses come from the real timeline, not manual
replacements of the mouth. These are estimated classes, **not independently
verified phonemes or a perceptual quality pass**. The stock voice is `af_heart`,
not Arena `voice-00` and not a clone. WAVs/models remain outside Git.

The native capture uses live eSpeak phoneme events at 0.65 seconds. Its reported
device is **SwiftShader Device (Subzero)**, `hardware_accelerated: false`. This is
software Vulkan, not a hardware benchmark and **not a Vulkan render of MPFB**.
The 67-joint test fixture retains the original android geometry and three morphs;
it is not a claim of equivalent visual complexity to the detailed human.

## Reproduce (prepared Linux development environment)

First follow the neural studio setup and install its pinned assets/dependencies.
Then build both actual renderers:

```sh
.venv/bin/python tools/bootstrap_sandbox.py
.venv/bin/python tools/build_neural_studio.py
.venv/bin/python tools/neural_studio_server.py --bind 0.0.0.0 --port 8084 \
  --sessions artifacts/readme-capture-sessions
```

In another terminal, from the repository root:

```sh
JALI_REVIEW=1 node tools/smoke_neural_studio.cjs http://127.0.0.1:8084
.venv/bin/python tools/capture_readme.py \
  --session-root artifacts/readme-capture-sessions --software-vulkan
```

Use a new disposable session directory, not a directory containing personal
recordings. Server startup cleans old session UUID directories in its own store.
The browser review checks cancellation/retry, the real CPU generation pipeline,
WAV/rig identity, rendered gaze, closure/style pixel equality, stop/reset and
all nine estimated classes. The publisher admits only the fixed public synthetic
corpus and verifies WAV/rig hashes before copying three real canvas exports. It
then runs the native renderer afresh and converts its raw RGBA output to PNG.

Omit `--software-vulkan` only when the configured native Vulkan runtime works on
your system. The recorded device/hardware flag will reflect that runtime.
The captures are not live-FPS, physical AV-sync or target-laptop acceptance evidence.

## Character attribution

The human is the **CC0 MPFB/MakeHuman** avatar distributed by TalkingHead:
[upstream pinned asset/license statement](https://github.com/met4citizen/TalkingHead/blob/2afe6d79779313db8909badebf46f9805a6c7b70/README.md).
The build preserves that explicit model license statement and the CC0 legal text
under the generated studio's `licenses/` directory. Three.js/meshoptimizer and
other dependencies keep their own licenses; CC0 is not a blanket license for
all TalkingHead assets. The android fixture is authored by this project in
`tools/make_character.py`. See the [human-head guide](human-head-demo.txt) and
[neural speech provenance](local-neural-speech.md) for the pinned asset details.
