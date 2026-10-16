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
| M1 | Local neural speech | CPU inference proven on Linux; listening review and Windows verification remain | New text generates playable speech locally, with reviewed artifacts and measured CPU cost |
| M2 | Automatic end-to-end generation | Delivered Linux/Windows-hosted WebGL prototype; new form-to-face sessions passed | One action produces and plays a newly synthesized, clip-driven performance |
| M3 | Better lip-sync fidelity | Partial: short-cue/end-rest fixes and repeatable nine-class review checks pass | Rig tuning, independent reference checks, and full-utterance quality review |
| M4 | Detailed character in Vulkan | Not integrated | Native engine renders the richer textured rig with verified deformation |
| M5 | Expressive facial performance | Basic procedural/manual controls only | Controllable, evaluated speech-related expression and gaze/gesture behavior |
| M6 | Streaming and interruption | Partial: whole-utterance playback works | Bounded incremental audio/face playback with cancellation and recovery |
| M7 | Windows performance and packaging | Partial: Windows backend and one-command benchmark passed hosted CI; target laptop and installer unverified | Measured target-device results and a tested, understandable launcher/package |
| M8 | Asset workflow and final QA | Partial: fixtures, provenance and tests exist | Reliable asset round trips, real AV measurements, and release review |

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

**Boundary:** the detailed human is currently a separate WebGL demo. The recordings
were generated externally. These successes do not establish local neural TTS,
learned emotional facial solving, Windows performance, or native support for this model.

## M1 — Local neural speech

**CPU inference checkpoint passed.** Kokoro-82M v1.0 q8 with its stock `af_heart`
voice generated two new WAVs locally on Linux using ONNX Runtime CPU only.
Listening review, broader tests and Windows verification remain open. The older
Chatterbox cloning adapter remains a separate, untested path.

See [the measured CPU experiment](local-neural-speech.md). This is not yet wired
into the face viewer, and it does not reproduce the earlier Arena `voice-00`.

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

- [ ] Compare the baseline against a permitted local aligner or trustworthy provider timings.
- [ ] If adding a forced aligner, review/pin its weights and validate its own outputs.
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

**Depends on:** the already available licensed character. This follows the first
working local-speech/WebGL integration, rather than blocking it.

- [x] Audit the optimized asset's static extensions/counts/targets against the native profile; 67-joint/66-target multi-mesh/material gaps are recorded, not silently removed.
- [ ] Choose an explicit supported native profile and report unsupported features clearly.
- [ ] Support the actual skeleton/palette needs; do not silently truncate the 67-bone rig.
- [ ] Preserve hierarchy, mesh transforms, inverse bind matrices and joint weights.
- [ ] Support the required named facial targets and consistent target ordering.
- [ ] Apply matching facial animation to the main face and secondary meshes.
- [ ] Add the necessary UV, texture and material paths.
- [ ] Handle normals/tangents, color spaces, transparency and relevant PBR properties.
- [ ] Decide whether to decode Meshopt at import or generate a separate native-ready asset.
- [ ] Verify resource limits, descriptor layouts and buffer bounds.
- [ ] Verify upload/deformation/raster barriers and in-flight resource lifetimes.
- [ ] Compare deformed positions and normals against a CPU reference.
- [ ] Compare canonical poses against the known-good WebGL presentation.
- [ ] Run Vulkan validation layers and fail on relevant errors.
- [ ] Validate on real target hardware, not only software Vulkan.
- [ ] Connect the same audio/cue session contract to the native character renderer.

**Exit gate:** the detailed human is genuinely rendered and animated by the native
Vulkan path, with supported features stated and deformation evidence retained.

## M5 — Expressive facial performance

**Current baseline:** procedural blinking/head drift and manual styling. Neither
constitutes inferred emotion or a learned facial performance.

- [ ] Separate speech articulation, expression, gaze and head-motion control layers.
- [ ] Define control ranges, blend priorities and conflict handling.
- [ ] Ensure expressions do not prevent lip closures or distort pronunciation poses.
- [ ] Add intentional gaze targets and evaluated eye behavior.
- [ ] Improve blink timing without labeling it emotion inference.
- [ ] Add restrained speech-related head gestures with user controls.
- [ ] Support explicit style instructions such as neutral, warm or attentive.
- [ ] Evaluate an optional permitted learned facial solver only if its resource needs fit the project.
- [ ] If using text/audio style estimation, label uncertainty rather than claiming to know a speaker's feelings.
- [ ] Evaluate emotional speech prosody separately from visual expression.
- [ ] Review expressions for jitter, repetition, overshoot and uncanny combinations.
- [ ] Keep an option to disable expressive motion and retain plain lip-sync.
- [ ] Collect user review of naturalness on multiple utterances.

**Exit gate:** controllable, reviewed expressive behavior that improves the
performance without breaking articulation. The implementation method stays disclosed.

## M6 — Streaming and interruption

**Current baseline:** whole-utterance synthesis/analysis plus controllable playback.
Streaming playback is not the same as incremental neural generation.

- [ ] Determine whether the selected TTS model genuinely supports incremental output.
- [ ] If sentence batching is used instead, label it accurately and evaluate boundary quality.
- [ ] Define chunk IDs, ordering, sample rate, starting sample offsets and end-of-stream behavior.
- [ ] Run inference/analysis outside render and audio callbacks.
- [ ] Introduce bounded audio and facial-data queues.
- [ ] Define lookahead and buffering policy for cues that need future audio.
- [ ] Use playback sample position as the shared clock.
- [ ] Handle underruns, late chunks, missing chunks and resampling explicitly.
- [ ] Cancel inference and flush stale audio/face data safely.
- [ ] Support stop/interruption followed by a clean new request.
- [ ] Return to neutral on cancellation or failure.
- [ ] Test backpressure and overlapping request attempts.
- [ ] Measure first-playable-audio latency separately from steady-state throughput.
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
- [ ] Build/run the native Vulkan path on Windows, including required process/IPC changes.
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

- [ ] Choose a launcher/package layout and document prerequisites.
- [ ] Provide understandable model setup with integrity/license checks.
- [ ] Include required runtime libraries and notices where redistribution is permitted.
- [ ] Avoid requiring the user to manage multiple terminals for normal use.
- [ ] Show actionable errors for missing models, drivers or dependencies.
- [ ] Keep recordings/models/cache out of Git and public logs.
- [ ] Explain which operations work offline after setup.
- [ ] Document cache cleanup, updating and uninstalling.
- [ ] Test a clean Windows installation/user profile, not only the developer environment.

**Exit gate:** a tested, understandable Windows launch path with honest target-device
measurements and an appropriate quality/performance configuration.

## M8 — Broader asset workflow and final QA

### Asset pipeline and optimization

- [ ] Preserve a canonical licensed DCC/source asset and documented rig schema.
- [ ] Pin chosen import/export tools and versions.
- [ ] Test source-to-runtime-to-source pose preservation where supported.
- [ ] Verify coordinate systems, units, handedness, winding and scale.
- [ ] Verify skinning, facial deltas, animated joint transforms and animated morph weights.
- [ ] Verify normals, tangents, UVs, materials, transparency and texture references.
- [ ] Add malformed/unsupported-feature fixtures for the expanded native profile.
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

**Delivered collector:** after Windows setup, run `windows/benchmark.ps1` on the
actual laptop and inspect/share `artifacts/jali-benchmark-report.json` if comfortable.
[Instructions and limits](windows-benchmark.md). M3 references must be independently
marked on the newly recorded WAVs; no rig strengths have been declared tuned.
M4 is at static audit only; implementing a rich native profile/ABI is still open.


**Early browser checkpoint prepared:** see [the extraction/review instructions](windows-playback-checkpoint.txt). The pack needs no Python or models for playback and exports explicit user notes plus visible-tab render observations. Windows-hosted Chrome HTTP/file playback passed separately from Linux neural synthesis in eight-job Actions run 38841826083. See [checkpoint evidence](playback-checkpoint.md). The separately ported developer backend subsequently passed nine-job run 38843451199; neither hosted check finishes target-device M7 acceptance.


**Windows target checkpoint + M3 quality review:** use the developer setup in
[Windows neural studio](windows-neural-studio.md) to generate new text on the
actual laptop, then listen to and inspect a connected new-text performance,
then tune pronunciation/articulation/transition timing on the actual rig. Use the
new public corpus and review page; do not equate passing morph contracts with
correct phoneme alignment. Fresh hosted neural CI passed in run 38837436553. Keep the
working M2 baseline. After this review, perform the early M7 Windows laptop
checkpoint before investing in native Vulkan expansion or more complexity.

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
| 2026-10-16 | Delivered isolated one-command Windows benchmark (actual PowerShell entry point passed in nine-job run 38844926069); six local fresh samples, 87 Python/12 JS tests. Added exact-WAV independent-reference templates/comparison and static M4 blockers for 8 meshes/skins, 67 joints, 66 targets and materials. No independent alignment, rig tuning, rich Vulkan rendering or target-laptop acceptance is claimed. |
| 2026-10-16 | Windows x64 developer backend passed three actual new CPU recordings, Windows exact-WAV/dialog analysis and live Chrome face checks. All nine Actions jobs passed; pipeline 4.99–5.30 s, worker peak working set 291–297 MiB on the runner. Added platform pins, safe extraction, Windows cleanup/UTF-8 handling and developer PowerShell launchers; target laptop/installer/quality remain open. |
| 2026-10-16 | Added a self-contained laptop/browser playback checkpoint with half-speed review, notes and explicit JSON export. Render-completion measurements distinguish CPU submission time from GPU execution/physical AV latency. Public-corpus/hash admission checks and local HTTP/file tests passed. All eight Actions jobs passed, including actual Windows Chrome HTTP/file playback; target-device and local Windows speech tests remain open. |
| 2026-10-16 | M3 partial: corrected short-cue blending and actual-duration rest, 9 JavaScript tests and 67 Python tests passed; three fresh browser-generated utterances produced 22 review frames covering nine estimated classes. Human/independent alignment review remains open. All seven jobs passed in Actions run 38837436553; the real neural job took 3m22s after fixing a cold binary-download defect. |
| 2026-10-16 | M2 connected prototype passed two actual browser-form requests: new CPU WAV + dialog analysis + real facial morph playback, hashes, pause/seek, history and error/retention contracts. Added idle redraw avoidance and a portable new-text MP4. Windows/quality/streaming remain open. |
| 2026-10-16 | Local Kokoro q8 CPU inference passed on two new sentences: 8.83s / 7.00s of audio, generated in 3.64s / 3.44s; peak RSS 441 MiB. No face integration or Windows performance claim. |
| 2026-10-16 | Created this tracker from the agreed eight workstreams; recorded the native prototype and detailed-head/actual-WAV delivery; selected local stock neural speech as the next milestone. |
