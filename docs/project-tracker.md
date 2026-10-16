# Jali project tracker

Last status review: **2026-10-16**.

This is the ongoing checklist for our personal, noncommercial voice-to-face system.
It tracks delivered evidence separately from planned features. It is not a claim
that the full original vision has been implemented.

## Goal and constraints

**Main goal:** type new text -> permitted local neural speech -> analyze that
recording -> animate the detailed character -> synchronized playback.

- Target: Windows, Intel Core i5 10th-generation U-series, 16 GB RAM.
- CPU-first; do not require buying a discrete GPU or using a paid service.
- Prefer permitted pretrained weights; training from scratch is not a prerequisite.
- Reuse our existing stock voice recordings for regression testing.
- Use freely usable character assets with explicit per-asset license evidence.
- A stock synthetic voice is sufficient. Personal voice cloning is optional.
- Use the working WebGL character first; integrate the richer character into Vulkan afterward.
- Do not promise target-laptop speed, voice quality, or physical AV accuracy before measurement.
- GitHub Actions is finite build/test capacity, not an always-on host or proof of GPU performance.

## How to use this tracker

- `[x]` = implemented and supported by the stated evidence, within its stated scope.
- `[ ]` = not finished, not verified, or not started; it is not silently counted as done.
- **Partial** = some components exist, but the milestone's exit gate has not passed.
- **Unverified** = a claim needs execution on the actual platform/device.
- Update the relevant boxes, evidence, blockers, and next action after each milestone.
- Do not substitute a rendered video for a live-performance benchmark.
- Do not substitute estimated visemes for verified phoneme alignment.
- Do not substitute a provider stub/admission test for successful neural inference.
- No arbitrary percentage-complete or calendar estimate is assigned.

## Status dashboard

| ID | Workstream | Current status | What closes it |
|---|---|---|---|
| B0 | Existing foundation | Delivered prototype, scoped below | Keep regression tests passing |
| M1 | Local neural speech | CPU inference proven on Linux/hosted Windows; user PC run works; listening review open | New text generates playable speech locally, with reviewed artifacts and measured CPU cost |
| M2 | Automatic end-to-end generation | Delivered Linux/Windows-hosted WebGL prototype; new form-to-face sessions passed | One action produces and plays a newly synthesized, clip-driven performance |
| M3 | Better lip-sync fidelity | Partial: calibrated Clear/Soft/Baseline closure/contact/tongue/transition controls and repeatable nine-class review checks pass | Rig tuning, independent reference checks, and full-utterance quality review |
| M4 | Detailed character in Vulkan | Implemented/validated on software Vulkan: rich head, same-WAV UI, CPU/GPU and source Three positions; target hardware open | Native engine renders the richer textured rig with verified deformation |
| M5 | Expressive facial performance | Separate manual layers, speech-priority warmth and gaze implemented; quality review open | Controllable, evaluated speech-related expression and gaze/gesture behavior |
| M6 | Streaming and interruption | Bounded sentence batching, verified next-audio prebuffer, 1,000-character paragraphs and cancel/retry delivered; not internal incremental inference | Bounded incremental audio/face playback with cancellation and recovery |
| M7 | Windows performance and packaging | Partial: source/frozen renderer/preset GUI, Launch/Stop/device doctor and one-command benchmark passed hosted CI; user-reported PC run works; licensing, signing and measured laptop acceptance open | Measured target-device results and a tested, understandable launcher/package |
| M8 | Asset workflow and final QA | Partial: fixtures, provenance and tests exist | Reliable asset round trips, real AV measurements, and release review |

## Character/workspace expansion — 2026-10-16

- [x] Bounded self-contained GLB validation; explicit bone/morph alias maps; hash-bound reusable character packages and separate custom-studio preparation.
- [x] Prepared lower-detail mesh/textures: 53,116 / 83,686 vertices/triangles → 33,520 / 37,842; 512px textures, verified LOD loading, 2 FPS natural-idle cap and explicit scene/audio unload.
- [x] Dialogue queue up to 128 turns / 20,000 characters; pause/resume, sentence navigation, owned-job interruption, server-side saved WAV/cue archives and verified replay after six-session eviction.
- [x] Opt-in loopback command/event broker; private key file, bounded commands/events, single browser lease, at-most-once semantics and a standard-library client.
- [x] Eight validated cast profiles; separate explicitly installed stock voice/speed/calibration/manual performance/appearance, pinned per-job snapshots. One active prepared mesh, speaker and inference worker; not concurrent distinct avatars.
- [x] Optional unsigned personal per-user installer source, dependency/integrity doctor, reinstall/update and data-preserving uninstall test; explicit personal-use acknowledgement.
- [x] Local 142 Python / 33 JS, secure-browser dialogue/storage/API/LOD/unload fixture and mapped synthetic GLB import passed.
- [x] Actual Blender 4.0.2 import/export: 16 world-space poses, all 13 required morphs; maximum error 8.702152625862784e-8 < 0.001. Genuine af_bella/am_michael CPU recordings and saved turn-taking passed locally.
- [x] Hosted Windows source speech/live face, frozen app with Python/Node/gh removed from PATH, and unsigned clean-profile install/update/uninstall passed in [38957696799](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38957696799/job/117164609631).
- [ ] Final full-workflow regression after cast persistence/export isolation and explicit offscreen-selector scrolling. Run 38957696799 remains failed: Linux genuine smoke timed out selecting an above-viewport quality control; other dependent jobs were skipped. A focused reproduction verified explicit scrolling, but a full local rerun still stalled waiting for stability after mobile-to-desktop resizing. Responsive checks now run last, leaving export in its original desktop viewport; final acceptance is still pending.
- [ ] Broad production-avatar/DCC acceptance, simultaneous distinct-mesh scene management and measured target-device budgets.
- [ ] Public release licensing/source/provenance approval; engineering inventory/gates added, NOT legal clearance. Signing optional for personal use.

[Contracts, setup, quotas and limitations](workspace-upgrades.md). Existing gates
below are not automatically closed by these scoped implementations.

## Creative upgrades 5–9 — 2026-10-16

- [x] Named rig-scoped calibration profiles with bounded import/export and browser persistence.
- [x] Optional deterministic irregular blinks, eased gaze, eye-contact and head-motion controls; native/JS numerical parity.
- [x] Five manual styles, intensity and bounded timed expression editor with speech-mouth protection.
- [x] WebGL light/material/background/camera controls and actual optional FXAA rendering.
- [x] User-facing fixed-clock JSON/CSV timelines and offline fixed-clock VP8/Opus WebM with verified source-WAV identity, one pose row per video-frame submission, repeat-export and cancellation cleanup.
- [x] Local 132 Python / 31 JS tests; real-head Chromium + FFmpeg audio/video decoding (explicit non-speech encoder fixture), repeated exports and exact timeline/frame pose parity.
- [x] Separate newly synthesized stock-Kokoro local speech export: 1.792 s / 54 frames; final full protocol with browser security enabled and CPU-owned frames: 3.46 s / all 104 decoded frames, verified WAV/cue identity.
- [x] Hosted genuine neural export, native artistic layers and Windows/package regression: **all 11 jobs passed** in [38945207804](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38945207804) for implementation `d4743f3`. Initial run 38939255761 failed Linux live capture; 38942919396 exposed a GPU-texture encoder flush stall. Resolved with CPU-owned RGBA handoff, bounded encoder waits and pending-flush cancellation; prior failures retained in [evidence](evidence/creative-upgrades-actions.json).
- [ ] Human motion/material review, target-device/physical AV and reverse-DCC acceptance.

[Controls, file formats and renderer limits](creative-upgrades.md). Appearance/video
capture are explicitly WebGL-only; facial timelines and authored performance also
support native. Existing legal/release gates remain open.

## Four-upgrade implementation — 2026-10-16

- [x] Low/Balanced/High plus custom resolution/FPS; actual WebGL framebuffer checks.
- [x] Actual-frame observation JSON and manually applicable conservative recommendation.
- [x] Clear/Baseline/Soft with bounded closure/contact/tongue/transition calibration;
  exhaustive JS/Python profile and boundary parity.
- [x] Verified bounded next-audio prebuffer; actual browser hits, controlled-delay
  gap comparison, Stop/stale-response cleanup, persisted settings.
- [x] Paragraph budget 1,000 characters / 12 chunks; producer/PCM bounds preserved.
- [x] Source/frozen renderer/preset chooser, free-port startup and recovery doctor.
- [x] Local 130 Python / 22 JavaScript tests and real-head browser regression.
- [x] All 11 hosted jobs passed: Windows frozen GUI launch/Stop/doctor, real
  535-character neural paragraphs, and 256/512/768 native images.
  [Run 38935343354 / source 00d9859 evidence](evidence/four-upgrades-actions.json).
- [ ] Target i5 measurements and human lip-seal/contact/tongue/naturalness approval.

[Implementation and usage](four-upgrades.md). The browser transport fixture is
explicitly non-speech; it is not a replacement for genuine neural integration.
Existing independent-reference/physical AV/legal gates remain open.

## B0 — Foundation already delivered

### Native engine prototype

- [x] C++17 project and model-free CPU contract tests.
- [x] Built-in eSpeak speech with its own phoneme timing events.
- [x] Original simpler rigged GLB fixture.
- [x] Strict-profile native GLB importer, not a universal glTF/FBX importer.
- [x] Vulkan compute morphing/skinning and indexed rasterization for that supported profile.
- [x] Native-frame browser playback following an audio clock, with pause/seek.
- [x] CPU/GPU position comparison and malformed-input regression tests.
- [x] Earlier GitHub Actions build/sanitizer/native software-Vulkan validation run.

### Detailed human and the existing neural clips

- [x] Select a detailed MPFB/MakeHuman character with explicit upstream CC0 evidence.
- [x] Verify source model against its pinned GitHub blob/hash.
- [x] Prepare an optimized model retaining 67 bones and 66 main-mesh facial controls.
- [x] Retain matching facial controls on relevant teeth/tongue/brow/lash meshes.
- [x] Reuse all three original stock neural WAVs without changing their hashes.
- [x] Run actual-WAV Rhubarb/PocketSphinx analysis with dialog guidance.
- [x] Retarget the resulting estimated A-H/X mouth classes in the WebGL viewer.
- [x] Drive interactive poses from audio time, including pause/seek and rest at the end.
- [x] Provide optional procedural blinking/head movement and manual expression styling.
- [x] Test distinct mouth renders with procedural movement disabled and actual morph weights checked.
- [x] Test HTTP and offline file playback, all three WAVs, and sync on/off.
- [x] Produce a 512 x 512, 15 fps lip-closure MP4 using the actual neural WAV and the same cue solver.
- [x] Validate decoded GLB geometry: zero errors, nine retained warnings.
- [x] Deliver a checksummed offline ZIP, model/license evidence, and portable MP4.
- [x] Run 44 Python tests and six pure-JavaScript viseme tests at the latest delivery.

**Historical B0 boundary:** these original captures used a separate WebGL demo
and externally generated recordings. Later M1/M2/M4 milestones now establish
local CPU speech and rich native support; B0 alone did not establish them.

## M1 — Local neural speech

**CPU inference checkpoint passed.** Kokoro-82M v1.0 q8 with its stock `af_heart`
voice generated two new WAVs locally on Linux using ONNX Runtime CPU only.
The same CPU pipeline and frozen application now pass hosted Windows checks;
the user reports a working PC run. Independent listening review and quantitative
target-laptop acceptance remain open. The older Chatterbox cloning adapter remains
a separate, untested path.

See [the measured CPU experiment](local-neural-speech.md) and connected M2/M4
studio below. Stock `af_heart` does not reproduce the earlier Arena `voice-00`.

### Selection and permission

- [ ] Define a small representative new-text test set: short sentence, long sentence, punctuation, names and numbers.
- [x] Evaluate a CPU-suitable stock neural TTS candidate before committing to a heavier cloning model.
- [ ] Review the exact code, checkpoint, tokenizer, vocoder and output-use terms.
- [x] Verify downloadable artifacts are obtainable from permitted sources; do not assume default model hosting is reachable here.
- [x] Pin versions and hashes; document download size, disk space and dependencies.
- [x] Keep model artifacts outside Git and public CI caches/artifacts.

### Successful local execution

- [x] Install the selected runtime in an isolated environment.
- [x] Load the reviewed pretrained weights successfully.
- [x] Synthesize a genuinely new sentence locally on CPU.
- [x] Validate the WAV's sample rate, encoding, duration, amplitude and completeness.
- [ ] Listen for intelligibility, pronunciation errors, clipping, repetition and missing words.
- [x] Record cold start, warm generation time, real-time factor and peak RAM.
- [x] Verify local execution does not silently call a hosted speech API.
- [x] Record model provenance and clear synthetic-voice disclosure.
- [ ] Repeat on the target Windows laptop before making target-hardware claims.

**Exit gate:** arbitrary new test text becomes understandable, playable speech from
reviewed local weights. Publish actual measurements and failures, not just an adapter test.

## M2 — Automatic end-to-end generation

**Connected prototype delivered.** New text now runs through local Kokoro CPU
synthesis, actual-WAV/dialog Rhubarb analysis and the detailed WebGL character in
one UI action. Two real browser-form sessions passed. See [the studio guide](neural-studio.md).
Better alignment, speech/face quality review and Windows validation remain separate gates.

- [x] Connect text input to the proven local TTS worker.
- [x] Define a session record linking text, voice/model version, WAV hash, cue data and rig version.
- [x] Feed the newly generated WAV and its actual dialog into the analyzer.
- [x] Validate cue coverage, finite times, valid classes and matching audio provenance.
- [x] Never attach eSpeak timing or an earlier recording's cues to a new neural WAV.
- [x] Load the new WAV and generated cues into the detailed WebGL viewer.
- [x] Reset the old audio, mouth pose and playback state when switching sessions.
- [x] Provide one clear Generate and Play action with visible progress stages.
- [x] Handle synthesis, analysis and playback errors without a hidden substitute voice or fake animation.
- [x] Test repeated requests and ensure sessions cannot accidentally mix audio and face curves.
- [x] Test play, pause, seek, restart and natural completion for newly generated audio.
- [x] Add an automated local integration test, separate from model-free tests.
- [x] Run fresh neural synthesis + actual audio analysis + browser playback in hosted GitHub Actions; seven-job run 38837436553 passed.
- [x] Demonstrate at least two previously unused sentences through the complete pipeline.

**Exit gate:** one action turns new text into locally generated speech and the
matching animated human performance. A sequence of manual scripts is not the finished UI.

## M3 — Better lip-sync fidelity

**Current baseline:** nine estimated Rhubarb classes, approximate retargeting and
blending capped at 35 ms / 35% of each cue. Short closures retain their central
pose, and actual audio completion forces rest despite timing trim. Three fresh
synthetic corpus recordings passed local browser checks, producing 22 neutral
frames across all nine classes. See [M3 evidence and review](neural-articulation.md).
This is not verified phoneme-level alignment.

### Rig-specific articulation

- [ ] Inspect P/B/M lip closure for leaks, penetration and excessive compression.
- [ ] Inspect F/V lip-to-teeth contact.
- [ ] Inspect rounded O/U/W poses and transitions to spread vowels.
- [ ] Inspect wide/open vowels, jaw opening and cheek behavior.
- [ ] Inspect tongue/teeth behavior where the rig supports it.
- [ ] Tune per-shape strengths without treating unrelated corrective controls as interchangeable.
- [ ] Tune context-sensitive transition timing and reduce abrupt or chattering poses.
- [ ] Preserve a stable neutral pose and appropriate silence behavior.

### Alignment and independent evaluation

- [x] Generate empty reference templates bound to each exact benchmark WAV/text; do not derive expected events from Rhubarb.
- [x] Add an attributed-reference comparator with actual-WAV checks, window coverage and signed boundary differences; synthetic unit tests are not actual alignment validation.

- [x] Add a permitted pinned two-pass PocketSphinx phone-alignment crosscheck of actual WAVs; same Sphinx family, **not** independent ground truth. All three corpus WAVs produced 105 phones locally.
- [ ] Complete a genuinely independent reference/quality review; do not promote the crosscheck to ground truth.
- [x] Pin optional PocketSphinx 5.0.4, retain code/acoustic-model notices, hash dictionary/model files and validate full word/phone ordering; no bundled aligner is added to the consumer build.
- [ ] Handle inaccurate transcripts, unknown words and low-confidence alignment explicitly.
- [ ] Create independently reviewed expected events for the three existing clips.
- [x] Add unseen utterances so tuning is not limited to the original recordings.
- [x] Add short-cue hold and actual-audio-end/negative-trim regressions.
- [x] Capture actual mesh renders for neutral review alongside fresh synthetic WAVs.
- [ ] Review the whole utterance, not just first-mouth-motion onset.
- [ ] Test long-sentence drift, short silences, plosives and repeated sounds.
- [ ] Check rendered mouth motion, not only requested curve values.
- [ ] Retain side-by-side comparison renders and record user quality feedback.

**Exit gate:** demonstrably better articulation and timing on both reference and
unseen speech, with documented review. No universal millisecond accuracy claim is assumed.

## M4 — Detailed character inside Vulkan

**Implemented profile/evidence:** [rich-v1 guide](rich-vulkan-and-streaming.md),
[real images and CPU/GPU/source comparisons](images/native-human-evidence.json).
Current source Three/native position maximum component error: 3.58e-7 across
53,116 vertices × six poses. Native lighting is not pixel-identical to WebGL.
Hosted Vulkan validation and all ten jobs passed in [run 38905755693](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38905755693).

**Depends on:** the already available licensed character. This follows the first
working local-speech/WebGL integration, rather than blocking it.

- [x] Audit the optimized asset's static extensions/counts/targets against the native profile; 67-joint/66-target multi-mesh/material gaps are recorded, not silently removed.
- [x] Choose an explicit supported native profile and report unsupported features clearly.
- [x] Remove the 64-joint capacity blocker: 128-joint C++/GLSL ABI, weighted 67/128-joint GPU-vs-CPU fixtures and device buffer checks. Full rich-asset hierarchy integration remains below.
- [x] Preserve hierarchy, mesh transforms, inverse bind matrices and joint weights.
- [x] Support the required named facial targets and consistent target ordering.
- [x] Apply matching facial animation to the main face and secondary meshes.
- [x] Add the necessary UV, texture and material paths.
- [x] Handle normals/tangents, color spaces, transparency and relevant PBR properties.
- [x] Decide whether to decode Meshopt at import or generate a separate native-ready asset.
- [x] Verify resource limits, descriptor layouts and buffer bounds.
- [x] Verify upload/deformation/raster barriers and in-flight resource lifetimes.
- [x] Compare deformed positions and normals against a CPU reference.
- [x] Compare canonical poses against the known-good WebGL presentation.
- [x] Run Vulkan validation layers and fail on relevant errors; actual detailed-head hosted job passed.
- [ ] Validate on real target hardware, not only software Vulkan.
- [x] Connect the same audio/cue session contract to the native character renderer.

**Exit gate:** the detailed human is genuinely rendered and animated by the native
Vulkan path, with supported features stated and deformation evidence retained.

## M5 — Expressive facial performance

**Current baseline:** deterministic separate speech/style/blink/head/manual-gaze layers, with speech-priority warmth suppression. These are manual/cosmetic controls, not inferred emotion or a learned facial performance. See [implementation details](performance-controls.md).

- [x] Separate speech articulation, expression, gaze and head-motion control layers.
- [x] Define bounded control ranges and speech-priority warmth handling; unit tests and full-closure pixel comparison cover the implemented rules.
- [ ] Ensure expressions do not prevent lip closures or distort pronunciation poses.
- [ ] Evaluate intentional gaze targets/eye behavior; bounded forward/left/right/down eye-bone offsets are implemented and render-tested, not naturalness-reviewed.
- [ ] Improve blink timing without labeling it emotion inference.
- [ ] Add restrained speech-related head gestures with user controls.
- [x] Support explicit manual neutral, warm and attentive styles (not emotional TTS prosody).
- [ ] Evaluate an optional permitted learned facial solver only if its resource needs fit the project.
- [ ] If using text/audio style estimation, label uncertainty rather than claiming to know a speaker's feelings.
- [ ] Evaluate emotional speech prosody separately from visual expression.
- [ ] Review expressions for jitter, repetition, overshoot and uncanny combinations.
- [x] Keep neutral styling, forward gaze and a procedural-motion toggle for plain lip-sync.
- [ ] Collect user review of naturalness on multiple utterances.

**Exit gate:** controllable, reviewed expressive behavior that improves the
performance without breaking articulation. The implementation method stays disclosed.

## M6 — Streaming and interruption

**Current baseline:** bounded sentence-batched early playback, max two pending/eight total chunks, integer PCM offsets and per-chunk exact-WAV analysis. Actual cancellation/retry and completed sample-concatenated replay passed. [Implementation and measured limits](rich-vulkan-and-streaming.md). This is **not** internal incremental Kokoro or gapless audio; human boundary/prosody review remains open.
Streaming playback is not the same as incremental neural generation.

- [x] Determine whether the selected TTS model genuinely supports incremental output.
- [x] If sentence batching is used instead, label it accurately and evaluate boundary quality.
- [x] Define chunk IDs, ordering, sample rate, starting sample offsets and end-of-stream behavior.
- [x] Run inference/analysis outside render and audio callbacks.
- [x] Introduce bounded audio and facial-data queues.
- [x] Define lookahead and buffering policy for cues that need future audio.
- [x] Use playback sample position as the shared clock.
- [x] Handle underruns, late chunks, missing chunks and resampling explicitly.
- [x] Cancel owned whole-utterance speech/analyzer child, hide partial media and clean up before reuse; cancellation resets the face. Bounded sentence queues are also cancelled/discarded.
- [x] Stop/reset playback and cancel/retry generation, tested through the real UI.
- [x] Return to neutral on cancellation or failure.
- [x] Reject overlapping whole-utterance requests while running/cancelling; tests cover retry and ready/cancel races. Chunk backpressure and acknowledgment ordering are tested.
- [x] Measure first-playable-audio latency separately from steady-state throughput.
- [ ] Test synchronization and memory over extended playback.

**Optional extension, not a prerequisite for typed-text completion:** microphone
input, speech recognition and turn-taking. An LLM conversation backend is not
silently added as a requirement of the current typed-text milestone.

**Exit gate:** incremental performance works with bounded resources and reliable
interruption, or the delivered non-streaming limitations are explicitly retained.

## M7 — Windows performance and packaging

**Target-device verification must happen on the user's laptop.** Sandbox and
hosted Linux/Windows CI results cannot stand in for it.

### Hosted Windows developer backend (not target-device acceptance)

- [x] Inventory official Windows analyzer bytes without executing, then pin archive/executable hashes.
- [x] Select Windows executable/resources with safe extraction and no Linux fallback.
- [x] Generate three genuinely new Windows CPU neural WAVs and analyze each with its script.
- [x] Exercise the live Chrome form-to-face pipeline on the Windows runner.
- [x] Record synthesis, analysis, total pipeline time and Windows worker peak working set.
- [x] Add explicit PowerShell setup/start developer scripts; clean consumer launcher experience remains unverified.
- [x] Preserve Linux real-inference/browser regression and cross-platform fast contracts.

Actual hosted metrics and remaining setup scope: [Windows neural studio](windows-neural-studio.md),
[Actions evidence](evidence/windows-neural-actions.json). All nine jobs passed in run 38843451199.

### One-command measurement collector

- [x] Add `windows/benchmark.ps1` after explicit setup; normal runs use a visible installed Chrome/Edge.
- [x] Collect repeated new CPU speech, model/import times, peak worker memory and renderer-update observations into one inspectable JSON.
- [x] Use an isolated session store/loopback port; never clear an interactive preview's recordings for a benchmark.
- [x] Test the actual PowerShell benchmark entry point on hosted Windows, not only equivalent Python commands.
- [ ] Collect and review the resulting report from the user's actual laptop.

See [benchmark, independent references and native blockers](windows-benchmark.md).

### Target-laptop execution and measurements

- [ ] Inventory Windows version, CPU details, integrated graphics/driver and available RAM.
- [ ] Run the selected neural TTS locally on Windows CPU.
- [ ] Run analysis and end-to-end playback on Windows.
- [ ] Test browser WebGL availability and hardware-acceleration behavior.
- [ ] Run native Vulkan on this physical laptop and measure its actual GPU/driver behavior. Windows process/IPC implementation and hosted software execution are complete.
- [ ] Measure cold start, model loading and time to first audio/face frame.
- [ ] Measure full generation time and real-time factor.
- [ ] Measure live rendering FPS/frame times and stalls.
- [ ] Measure peak RAM, model/asset disk space and cache growth.
- [ ] Measure synchronization across sustained playback.
- [ ] Repeat representative tests long enough to observe thermal/power effects.
- [ ] Define acceptable settings based on these results rather than invented budgets.
- [ ] Retest chosen reduced-quality/performance settings.

### Early browser-only slice (not the full Windows package)

- [x] Provide a self-contained playback/review ZIP without Python or speech models.
- [x] Export explicit notes and renderer-update/CPU-submission observations locally.
- [x] Test HTTP and file playback on hosted Windows Chrome and Linux Chromium.
- [ ] Collect repeated measurements and quality notes on the actual i5 laptop.
- [x] Port/test local speech and analyzer processes on hosted Windows x64; laptop acceptance remains separate.

### Usable package

- [x] Implement personal PyInstaller 6.16.0 onedir WebGL + optional native Vulkan layout and explicit launchers; actual frozen native execution passed hosted Windows with Python/Node/gh removed from the app PATH. [Build/licensing guide](windows-portable.md).
- [x] Provide understandable model setup with integrity/license checks.
- [x] Include personal-build speech/native runtime libraries and collected notices; manifest and actual frozen readback pass hosted.
- [ ] Establish complete corresponding-source/notices and combined-work obligations before public redistribution.
- [x] Avoid requiring the user to manage multiple terminals for normal use.
- [x] Fail closed on missing/changed bundled assets and dependencies, with offline JSON diagnostics and repair guidance; record server startup errors.
- [ ] Independently validate consumer-grade driver/bootstrap/SmartScreen failure UX on a clean Windows profile (including failures before Python starts).
- [x] Keep private recordings/speech weights/caches out of Git and public logs. Public synthetic corpus and explicitly licensed CC0 rig are documented artifact exceptions.
- [x] Explain which operations work offline after setup.
- [x] Document cache cleanup, updating and uninstalling.
- [ ] Test a clean Windows installation/user profile, not only the developer environment.

**Exit gate:** a tested, understandable Windows launch path with honest target-device
measurements and an appropriate quality/performance configuration.

## M8 — Broader asset workflow and final QA

### Asset pipeline and optimization

- [ ] Preserve a canonical licensed DCC/source asset and documented rig schema.
- [x] Pin NodeIO/Meshopt, Three, Pillow and validation tools for the decoded GLB export.
- [ ] Test source-to-runtime-to-source pose preservation where supported.
- [x] Verify chosen source/canonical coordinate and bind transforms via all-vertex source comparison and real native captures; this is scoped to rich-v1.
- [ ] Verify skinning, facial deltas, animated joint transforms and animated morph weights.
- [ ] Verify normals, tangents, UVs, materials, transparency and texture references.
- [x] Add tiny original rich multi-material/alpha/morph fixture and expand native malformed-input suite to 27 cases; tests remain model-free.
- [ ] Generate LODs without silently breaking facial controls or secondary meshes.
- [ ] Test active-shape budgets and compare visual quality against the canonical model.
- [ ] Profile representative character counts before claiming multi-character scale.

### Playback quality and regression coverage

- [x] Add the detailed-head/new-text pipeline to appropriate automated CI coverage.
- [x] Keep fast model-free tests separate from heavyweight licensed-model execution.
- [ ] Test long utterances, silence, rapid transitions, repeated generation and recovery.
- [ ] Capture actual presented frames and audio for independent AV evaluation.
- [ ] Measure audio-output/display latency on the intended device.
- [ ] Evaluate sync error over the whole utterance, including variation and drift.
- [ ] Retain human review of speech intelligibility and facial quality.
- [ ] Verify final package hashes and source/model provenance.

### Dependency, privacy and release checks

- [ ] Complete the inventory for code, weights, tokenizers, vocoders, assets and media tools.
- [ ] Confirm the intended personal-use permissions for every selected component.
- [ ] Review redistributed dependencies' notice/source obligations; personal use is not a blanket exemption.
- [ ] Decide on a project distribution license only if/when the owner wants distribution.
- [ ] Review third-party model execution and keep sensitive files isolated.
- [ ] Keep private recordings, grants and checkpoints out of public CI artifacts.
- [ ] Document local data retention, cleanup and deletion.
- [ ] Preserve synthetic-speech disclosure and provenance.
- [ ] If network access is exposed beyond a local development setup, add the appropriate authentication and security controls.

**Exit gate:** the intended personal package passes documented functional, quality,
performance, provenance and privacy checks. Broader public distribution requires
its own additional review; it is not assumed by this tracker.

## Optional track — personal voice cloning

Not required for the main stock-voice system. Do not block M1/M2 on this track.

- [ ] Decide whether cloning is actually wanted.
- [ ] Obtain an authorized source recording and document its allowed scope.
- [ ] Review the exact cloning checkpoint/runtime and its CPU suitability.
- [ ] Implement actual reference conditioning; admission checks alone are insufficient.
- [ ] Test likeness, intelligibility and failure cases separately.
- [ ] Implement applicable authorization, expiry/revocation and deletion behavior.
- [ ] Preserve clear synthetic output disclosure.

## Agreed execution order

1. **M1:** prove new local neural speech on CPU with a permitted stock voice.
2. **M2:** connect it to actual-audio analysis and the existing human WebGL viewer.
3. **M3:** review/tune the resulting performance and improve alignment where needed.
4. **M7, early checkpoint:** benchmark the working vertical slice on the Windows laptop.
5. **M4:** bring the proven character/session pipeline into native Vulkan.
6. **M5/M6:** add expression and streaming incrementally, guided by performance results.
7. **M7/M8:** finish packaging, broader asset tests and final quality/release review.

Licensing, input validation, provenance and regression testing run throughout,
not only at the final step. Performance problems may require changing the model
or scope; a roadmap item is not a promise that an arbitrary model will run in real time.

## Current next action

The user reports the existing Windows developer command works on their PC.
The implementation now includes rich human Vulkan with the same neural WAV/cues,
native Windows binary-safe presentation, bounded sentence batching/interruption,
separate styling/gaze controls, phone diagnostics, and an optional personal frozen
Windows-native bundle with integrity checks and relocatable shaders. Actual
rendered human images remain in the README.

**All 11 hosted jobs passed** for `caa1e95` in
[run 38913502148](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38913502148).
That includes Windows native execution, full source-vertex/browser comparisons,
10020-frame protocol longevity plus detailed-head RSS checks, frozen native
speech/batches with Python/Node/gh stripped from PATH, and package tamper/missing
file/refusal/recovery checks. [Exact machine-readable evidence and failed attempts](evidence/windows-native-integrity-actions.json).
Local contracts: **123 Python / 17 JS / 12 CTest entries**. Hosted Windows Vulkan
has 11 CTest entries because the separate eSpeak live executable is not built.

The offline measurement test now deterministically covers the queued-reset-pause
startup race, actual-play cancellation, stale play completion and changed-speed
invalidation. It passed HTTP and file playback on hosted Windows and Linux.
This fixes a reproducible lifecycle defect; the older offline failure whose logs
were unavailable is retained, not retrospectively assigned a proven cause.

Next is genuine acceptance, not fabricated approval: independent phone/contact/
naturalness and whole-utterance review; quantitative target i5/16-GB hardware,
memory/latency/physical AV measurements; and release licensing/signing/security.
Internally incremental Kokoro/gapless streaming, general reverse-DCC compatibility,
LODs and multi-character scale are not silently inferred from bounded sentence
batches or this one preserved rig. No redistributable/signed consumer release is
claimed. Personal use remains the tested distribution scope.
See [native usage and limits](rich-vulkan-and-streaming.md), [personal build](windows-portable.md),
and [one-command laptop measurements](windows-benchmark.md).

## Evidence and existing deliverables

- [Windows x64 local speech/analyzer/live face and measured hosted results](windows-neural-studio.md)

- [M3 articulation checks and hosted CPU coverage](neural-articulation.md)
- [Connected neural studio and its limits](neural-studio.md)
- [Main project status and commands](../README.md)
- [Detailed human-head guide](human-head-demo.txt)
- [Native engine scope and tests](live-engine.md)
- [Earlier test pack](test-pack.md)
- [Technical review and original assumptions](technical-review.md)
- Viewer sources: `web/neural-head/`.
- Build/analyze/test tools: `tools/build_neural_head.py`, `tools/analyze_neural_clips.py`,
  `tools/validate_head.cjs`, `tools/smoke_neural_head.cjs`.
- Generated evidence: `artifacts/neural-head-demo/proof/` and `manifest.json`.
- Delivered interactive pack: `/home/user/Jali-Human-Head-LipSync.zip`.
- Delivered portable example: `/home/user/Jali-Human-Head-LipSync.mp4`.

Generated media/models are ignored by Git; source checklists and code remain in
the repository. Earlier architecture/review documents contain historical stages;
use this dated tracker and current evidence to judge present completion.

## Change log

| Date | Update |
|---|---|
| 2026-10-16 | Completed Windows native source/binary-pipe support and optional frozen native package with relocatable shaders, no runtime Node, strict installation integrity and external logs. Fixed queued-pause measurement ownership and preserved exact cross-platform corpus rig bytes. All eleven jobs passed in run 38913502148 (`caa1e95`); 123 Python / 17 JS / 12 local CTest entries and 10020-frame longevity pass. Human/physical laptop and public redistribution/signing gates remain open. |
| 2026-10-16 | Implemented rich-v1 textured human Vulkan pipeline and shared neural-session native UI; eight CPU/GPU and six all-vertex source Three probes, native media-clock browser playback, bounded sentence batches/cancel/retry, 105-phone forced-alignment crosscheck, personal frozen Windows build. Local 109 Python/17 JS/12 CTest entries pass; all ten jobs passed in run 38905755693, including frozen Windows and rich Vulkan. A prior non-reproduced offline-Windows failure is retained in evidence. Added actual native human README captures. Human/laptop/release acceptance remains open. |
| 2026-10-16 | Implemented owned-child cancellation/cleanup and stop/reset/retry; separate speech/style/head/blink/manual-gaze layers with closure pixel protection; expanded native palette to 128 with weighted 67/128-joint CPU/GPU tests. Added four real README renderer captures with provenance. Local 94 Python/15 JS/11 CTest entries and real browser review passed; all nine hosted jobs passed in Actions run 38847212709, including Windows neural/browser/benchmark and native Vulkan validation. Rich Vulkan, independent quality, incremental streaming and measured laptop gates remain open. |
| 2026-10-16 | Delivered isolated one-command Windows benchmark (actual PowerShell entry point passed in nine-job run 38844926069); six local fresh samples, 87 Python/12 JS tests. Added exact-WAV independent-reference templates/comparison and static M4 blockers for 8 meshes/skins, 67 joints, 66 targets and materials. No independent alignment, rig tuning, rich Vulkan rendering or target-laptop acceptance is claimed. |
| 2026-10-16 | Windows x64 developer backend passed three actual new CPU recordings, Windows exact-WAV/dialog analysis and live Chrome face checks. All nine Actions jobs passed; pipeline 4.99–5.30 s, worker peak working set 291–297 MiB on the runner. Added platform pins, safe extraction, Windows cleanup/UTF-8 handling and developer PowerShell launchers; target laptop/installer/quality remain open. |
| 2026-10-16 | Added a self-contained laptop/browser playback checkpoint with half-speed review, notes and explicit JSON export. Render-completion measurements distinguish CPU submission time from GPU execution/physical AV latency. Public-corpus/hash admission checks and local HTTP/file tests passed. All eight Actions jobs passed, including actual Windows Chrome HTTP/file playback; target-device and local Windows speech tests remain open. |
| 2026-10-16 | M3 partial: corrected short-cue blending and actual-duration rest, 9 JavaScript tests and 67 Python tests passed; three fresh browser-generated utterances produced 22 review frames covering nine estimated classes. Human/independent alignment review remains open. All seven jobs passed in Actions run 38837436553; the real neural job took 3m22s after fixing a cold binary-download defect. |
| 2026-10-16 | M2 connected prototype passed two actual browser-form requests: new CPU WAV + dialog analysis + real facial morph playback, hashes, pause/seek, history and error/retention contracts. Added idle redraw avoidance and a portable new-text MP4. Windows/quality/streaming remain open. |
| 2026-10-16 | Local Kokoro q8 CPU inference passed on two new sentences: 8.83s / 7.00s of audio, generated in 3.64s / 3.44s; peak RSS 441 MiB. No face integration or Windows performance claim. |
| 2026-10-16 | Created this tracker from the agreed eight workstreams; recorded the native prototype and detailed-head/actual-WAV delivery; selected local stock neural speech as the next milestone. |


## Runtime hardening follow-up (2026-10-16)

- [x] Remove native 10,000-frame lifetime cutoff; cap command input before allocation.
- [x] Binary-safe Windows pixel pipes and source-build/PowerShell native setup/launch.
- [x] Pin Vulkan headers/loader sources; explicitly opt into installed Chrome software ICD in CI.
- [x] Personal package per-file manifest, read-only offline verify mode and fail-closed startup.
- [x] Reject missing/modified/injected files, unsafe paths, links and case collisions; eight model-free tests pass locally.
- [x] Add actual frozen integrity/tamper/missing-analyzer checks and native longevity/RSS regression to CI.
- [x] New eleven-job hosted run, including **native** Windows Vulkan and frozen-package integrity: all passed in 38913502148 (`caa1e95`).
- [ ] Physical laptop GPU/driver/latency/memory/audio-output acceptance remains separate from hosted software tests.
- [ ] Independent human articulation/naturalness/reference review and redistribution/signing still require real evidence, not generated approval.

- [x] Implement optional frozen native bundle, relocatable shader paths, external logs and native-mode launcher.
- [x] Actually relocate native executable/shaders locally with original shaders hidden; detailed human readback passes.
- [x] Fix two Windows-only contracts: canonical short/long temporary paths and POSIX archive inventory separators.
- [x] Reproduce/reset queued-pause measurement ownership race deterministically; retain real-play cancellation and speed-change rejection tests.
- [x] Follow-up hosted verification includes optional frozen native execution, actual native browser readback, and guarded elevated Windows software-ICD registration/cleanup.

First hardening run `38908847040` completed with nine passing jobs, including
frozen integrity/tamper/missing-file checks and Linux longevity; Windows native
compiled but did not execute successfully (`VK_ERROR_INCOMPATIBLE_DRIVER` plus
two Windows-specific Python contract failures), and offline playback exposed the
queued-pause cancellation race. These are failures, not a native Windows pass.
The follow-up preserves secure loader behavior, explicitly registers/cleans up
the hosted test ICD, fixes paths/separators, and adds a deterministic queued-pause
regression alongside actual playback cancellation. Local contracts are now
119 Python / 17 JavaScript / 12 CTest entries; hosted results are still pending.

Second run `38910496941`: Windows native GPU/backend and all 11 CTest entries
passed after the explicit hosted ICD registration fix, but the subsequent public
session proof correctly rejected a different Windows-prepared GLB hash. The
Linux producer's exact prepared CC0 model is now staged with the public corpus;
platform-local PNG re-encoding is never accepted as the same rig. A regression
checks that exact producer bytes survive local preparation. Source LF checkout
rules make cross-platform source/retarget hashes reproducible.

The optional frozen-native app also correctly failed the stripped-PATH test:
its shared-shape adapter still launched Node. Shapes are now exported from the
single authoritative JS mapping **at build time**, bound to its source hash,
and read directly at runtime. Two model-free contracts and actual native JPEG
readback with an empty PATH validate that fix locally. The frozen Windows path
must still pass hosted; failures have not been reclassified as successes.
Local total is now 123 Python / 17 JS / 12 CTest entries.


### Verified final hardening checkpoint

Run **38913502148**, source **caa1e95d08e8235836f68dd142b5321577fcf4da**,
completed **all 11 jobs successfully**. This supersedes the pending statements
in the chronological attempt notes above, not their recorded failures.
Windows native execution, optional frozen native runtime, exact cross-platform
corpus/model binding, no runtime Node, package integrity/refusal/recovery,
post-runtime immutability and 10020-frame longevity are now hosted-verified.
No public executable, speech weights or Chrome driver binary was uploaded.
Independent human, physical-laptop/AV and redistribution/signing gates remain open.
