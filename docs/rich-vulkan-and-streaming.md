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
request; the former 10,000-frame lifetime cap has been removed, while each
protocol command remains capped at 16,384 bytes. Latency/readback is reported, not mislabeled as physical AV accuracy.
No off-box model calls occur during generation. Development preview tokens/origin
checks are not remote authentication; use localhost on your own machine.

Sandbox only: add `--software-vulkan`. On hardware Vulkan **omit** that option.
The displayed device/hardware flag is measured. Software rendering proves
correctness, not real-time hardware performance. Native Windows process pipes
use a bounded reader thread and binary stdio. Actual hosted rich-native Windows
execution and optional frozen-native playback pass; physical laptop hardware
execution/performance remains a separate acceptance gate.

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

## Hosted execution

Current [run 38913502148](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38913502148)
passed **all 11 jobs** for `caa1e95`, including native Windows CTest/backend,
same-WAV detailed-human browser/source comparison, longevity/RSS, the optional
frozen-native app and installation corruption/recovery checks. Exact job/step
results, artifact IDs/digests and failed attempts are in
[verification evidence](evidence/windows-native-integrity-actions.json).
Hosted Windows and local longevity use software Vulkan: not physical GPU proof.

Earlier foundation:

All ten jobs passed in [run 38905755693](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38905755693).
That includes actual CPU speech/batching on Linux/Windows, the frozen Windows
CPU/WebGL executable, and a separate detailed-human native job using the **same
public WAV/cue sessions**. The native job passes strict profile validation,
CPU/GPU and original-source vertex comparisons, native audio-clock playback,
speech-protected warmth/gaze checks, expired-response-after-Stop regression, and
Vulkan validation gates. [Evidence](evidence/rich-stream-portable-actions.json)
records exact source/job/step identities, local results and the prior unexplained
Windows offline-checkpoint failure; a subsequent pass is not proof of its cause.

## Windows native source build and longevity

After `windows/setup-neural.ps1`, install CMake and Visual Studio C++ x64 build
tools with the Windows SDK. Then run:

```powershell
.\windows\setup-native.ps1
.\windows\start-neural.ps1 -NativeVulkan
```

The explicit setup downloads checksum-pinned Vulkan Headers/Loader 1.3.290 and
tinygltf 2.9.3 source, compiles the loader and renderer, and places the loader next
to `build-live/jali_rich.exe`. No paid SDK is needed. It does not install or change
your GPU driver. This developer build is separate from the CPU/WebGL frozen app.
Default device selection still requires a working system Vulkan driver; a native
Windows source build is not proof that this laptop's GPU/driver works.

For an **explicit software test**, installed Chrome's SwiftShader may be selected
with `setup-native.ps1 -SoftwareForTesting`, followed by
`start-neural.ps1 -NativeVulkan -SoftwareVulkanForTesting`. The driver hash/path
are recorded in `artifacts/windows-native/build.json`; the Chrome DLL is not
published or bundled. CI uses this mode and compares the same public WAV/cues,
CPU/GPU poses, all original Three vertices and actual browser native playback.
Windows raw stdin/stdout use binary mode so pixel byte 0x0A is not expanded to
CRLF. Browser comparison now shares the installed-Windows-Chrome harness.

`tools/stress_native.py` exercises 10,020 repeated fixture frames beyond the old
lifetime cap, then 256 detailed-head frames across all nine cue poses. Repeated
poses must retain identical raw frame hashes. It samples native process resident
memory after warming each pose and rejects growth over max(64 MiB, 20% of the
baseline). This is a regression budget, not a promised laptop resource target.
It also tests oversized commands, CRLF quit and a final command without newline.
The command length is bounded **before allocation**, with no lifetime frame cap.
Synthetic longevity testing is not sustained physical audio/AV certification.

Native shaders now resolve beside the explicitly supplied face shader. The
optional [personal frozen-native bundle](windows-portable.md#optional-personal-native-vulkan-bundle)
uses a packaged shader directory, not baked build-machine paths. A real local
relocation test moved the EXE/shaders and hid the original shader directory;
the complete human still rendered successfully. Frozen Windows relocation and
stripped-PATH loading are separately covered by the new hosted package test.

For cross-platform corpus proof, use the **exact** prepared CC0 GLB published by
the Linux producer, not a Windows-local PNG re-encoding of it. CI stages that
licensed asset with the public review corpus and checks the clip's bound model
SHA before conversion. Original pinned source/license provenance is still
verified. Source LF checkout rules also preserve exact retarget hashes.

The native shape table is exported from `visemes.mjs` by
`tools/build_native_shapes.cjs` during explicit presentation preparation. Frozen
runtime reads the bundled version-bound JSON directly; it does not launch Node
or evaluate JavaScript. Source-only contracts have a checked-in generated table
and numerical JS/Python parity tests. Updating the authoritative JS mapping
requires regenerating that table. For local software-driver tests use a normal,
non-elevated shell; secure Windows loaders ignore environment driver overrides
when elevated. Only disposable hosted CI receives the temporary registry entry.
