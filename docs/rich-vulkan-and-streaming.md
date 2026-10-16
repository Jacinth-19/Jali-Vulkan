# Detailed Vulkan head and bounded sentence playback

## Real native character, not the earlier android fixture

The native `rich-v1` profile preserves the chosen CC0 MPFB/MakeHuman human:
**8 primitive groups, 53,116 vertices, 83,686 triangles, 68 palette nodes,
66 named targets and 7 materials**. The offline converter decodes Meshopt and
quantization, reconciles each mesh's common bind-shape transform, bakes it into
positions/deltas/normals and preserves original vertex correspondence. It rejects
inconsistent per-joint bindings rather than copying another mesh's skin.

Supported: four influences, up to 128 joints / 256 nodes / 80 morphs, named
position/normal deltas, multiple material ranges, UV0, sRGB base color, normal
mapping with derivative TBN, scalar metallic/roughness, alpha MASK/BLEND and
single/double-sided materials. Two paired 3084² RGBA atlases retain the current
character's diffuse/normal textures with wrap-aware padded borders. Normal and
base-color atlas dimensions must match; unsupported maps, material extensions,
authored tracks, nonzero default morphs and incompatible features fail explicitly.
This is not a universal glTF/FBX/DCC importer. Runtime files are capped at 192 MiB;
limits also cover aggregate vertices/indices/morph storage and Vulkan device buffers.

Canonical GLB validation permits **only** the known generated-tangent warning
(the shader uses derivative TBN). Other warnings/errors fail. CPU/GPU tests compare
positions **and normals** for eight actual named poses; original source Three.js
`SkinnedMesh.getVertexPosition` is separately evaluated across **every vertex of
all eight groups** at six real corpus cue-center poses. Source/reference vertex
agreement is not a pixel/lighting match or an articulation-quality score.

## Use the same neural WAV/cues with native Vulkan

Complete neural studio setup and a standard [native build](live-engine.md), then:

```sh
.venv/bin/python tools/build_native_head.py
node tools/validate_native_head.cjs artifacts/native-head/mpfb-native.glb artifacts/native-head/validation.json
.venv/bin/python tools/neural_studio_server.py --bind 127.0.0.1 --native-asset artifacts/native-head/mpfb-native.glb
```

In **Face renderer**, select **Native Vulkan**, then generate new text normally.
The browser verifies the exact WAV hash before playing; its `audio.currentTime`
selects native named morphs from that same session. Native mode suppresses WebGL
redrawing and displays actual native JPEG readback, not a prerecorded animation.
Pause/seek, sync/trim, speech-priority styling, procedural blink/head motion and
manual gaze remain separate controls. Native portrait camera and lighting differ
from the WebGL orbit view. The renderer is persistent, with only one in-flight
request; latency/readback is reported, not mislabeled as physical AV accuracy.
No off-box model calls occur during generation. Development preview tokens/origin
checks are not remote authentication; use localhost on your own machine.

Sandbox only: add `--software-vulkan`. On hardware Vulkan **omit** that option.
The displayed device/hardware flag is measured. Software rendering proves
correctness, not real-time hardware performance. Native Windows process pipes
use a bounded reader thread, but actual rich-native Windows/laptop execution is
still a separate acceptance gate; the portable CPU/WebGL package excludes it.

Offline render of a saved session (the original WAV is the audio input):

```sh
.venv/bin/python tools/render_native_session.py --manifest artifacts/neural-studio-sessions/SESSION_ID/manifest.json
```

Output includes actual cue-center PNGs, a source-WAV-bound MP4, eight CPU/GPU probes
and hashes. Video is offline, not a live FPS measurement. `--no-video` skips MP4.
The old strict three-morph/vertex-color fixture continues to run unchanged.

## Sentence-batched early playback

Check **Sentence-batched early playback** in the studio. This is bounded
**whole-sentence/chunk Kokoro inference + exact-chunk WAV analysis**, not internal
incremental Kokoro inference, gapless audio or a microphone conversation system.
At most **8 chunks**, **160 characters per chunk**, **2 unacknowledged chunks**,
**60 seconds of PCM** and **75 seconds awaiting consumer acknowledgment** are
allowed. One producer runs outside audio/render callbacks. No hidden resampling:
all chunks must share a sample rate. Integer absolute sample offsets bind chunks
to face diagnostics; actual media time drives each chunk's cues.

The browser verifies each WAV before loading it, plays in order, acknowledges only
after audio `ended`, and rests during underruns. Pause/slow consumers can expire;
late/missing/reordered data fails rather than playing another recording's face.
Stop/cancel removes pending audio/face data and permits retry after cleanup.
Transient chunks replace one viewer slot, not all user history. Successful
completion preserves a verified **sample-concatenated recording/cue timeline**
with chunk hashes/offsets; it does not automatically replay the entire recording.
Boundaries can have audible gaps and prosody changes. `stream-check.json` records
first-playable latency (from the successful POST response), inter-chunk gaps,
backpressure, cancellation/retry and concatenation checks. It is not a quality
acceptance or end-to-end user-click latency claim.

## Phone alignment diagnostics and remaining acceptance

An optional **PocketSphinx 5.0.4 two-pass forced aligner** now analyzes the actual
WAV and requested dictionary-normalized text, without reusing Rhubarb output:

```sh
.venv/bin/python -m pip install --no-deps -r tools/requirements-alignment.txt
.venv/bin/python tools/align_neural_session.py --manifest PATH/manifest.json --output artifacts/phone-alignment
```

It records exact original/resampled audio hashes, acoustic/dictionary file hashes,
word/phone intervals and critical P/B/M, F/V, L and silence-window comparisons.
Unknown words/numbers unsupported by normalization fail explicitly; there is no
invented pronunciation or substitute alignment. The wheel's code license and
acoustic-model notice are retained with diagnostics. This is a separate alignment
path but **related Sphinx acoustic family**, so it is deliberately **not declared
independent ground truth** and cannot populate an attributed human-reference
file automatically. Raw likelihoods are not calibrated confidence. Acoustic
phone windows are not necessarily visual gesture boundaries; no blind retuning
is applied from them.

Still external/unaccepted: independent phoneme/visible lip-contact/naturalness
review; whole-utterance human AV review; quantitative measurements on the user's
actual i5/16-GB Windows laptop; native Windows hardware proof; and redistribution
license/source review plus signing/consumer installer. These cannot truthfully be
closed by software-only assertions. See the [tracker](project-tracker.md) and
[personal portable-build guide](windows-portable.md).
