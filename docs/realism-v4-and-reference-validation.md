# V4 appearance, cross-tab ownership and independent validation

**Newer brow/blink/contact follow-up:** [implementation, actual renders and remaining acceptance gates](contact-and-blink-review.md). Historical v4 images/receipts below are not rebound to the newer rig/viewer. Previous 7cf2cda follow-up CI is now 12 core + 1 male successful; see its completed receipt.

2026-10-17. **Experimental WebGL assets and validation tools, not artistic or
physical acceptance.** Stock/native assets remain separate. The earlier 12+1
successful Actions receipts belong to source `61e0315`, not this implementation.

## Implemented

- Browser Web Locks serialize character renderer ownership for one origin and
  browser profile. A waiting live-studio tab creates no WebGL renderer and does
  not fetch/decode either GLB. Closing the owner or explicitly unloading lets the
  next tab initialize. Waiting and initializing requests can be cancelled.
  Initialization failures dispose resources before releasing ownership.
- Disposal covers geometry/material/texture/skeleton resources, postprocessing,
  environment render target and context loss before release. No timeout/heartbeat
  fallback that could create simultaneous owners. Unsupported contexts fail closed.
- Live full models now load from a local, SHA-verified URL after ownership, rather
  than being embedded in every page's JavaScript. Standalone offline checkpoints
  retain their embedded bytes; locks prevent their decode/render, not their
  embedded script allocation. Runtime never downloads remote character assets.
- Optional build-time appearance recipe for **both sexes**: original albedo detail
  retained at 1024px, gently tinted; 512px roughness zones and synthetic microheight
  normal; synthetic thin-region mask in normal alpha. These are **not scanned,
  measured or artist hand-painted textures**.
- Anchored tapered brow/lash ribbons retain source weights and all available
  POSITION morphs. Male gets an original short scalp-projected shell, directional
  ridges and original streak-color texture, not the shared ponytail. The tested
  male projection had zero missed rays. This is **not a strand groom**.
- Before compression, authoring asserts byte-identical body rest position/normal
  and all 66 body morph position/normal arrays (134 attribute hashes). Brows/lashes
  intentionally change geometry; their target names/anchor motions remain.
- Opt-in `scattering` appearance control, **default 0**, bounded to 0–0.25. One
  masked wrapped-diffuse lobe from the key light, no extra pass/draw or runtime
  texture allocation. Authored maps are additional prepared asset textures.
  This is **not physical subsurface scattering or measured thickness**.
  Old seven-key appearance settings remain valid; new settings persist the control. Rig-hash checks are unchanged: keep old packages/data for rollback rather than rebinding old recordings to a new model/viewer.

### Scope of the memory guarantee

Same origin means the same scheme, host **and port**. Different ports, browser
profiles, private contexts, apps and old builds do not share the lock. Close/reload
old build tabs on upgrade. A waiting tab still consumes ordinary page/JavaScript
memory; this is not a whole-browser or OS RAM cap. The server separately keeps
one shared CPU synthesis slot across both rigs.

## Build / inspect

After the existing explicit environment/model preparation:

```powershell
# Enhanced pair, male default; unsigned personal build. No native renderer.
.\windows\build-character-pair.ps1 -PersonalUseOnly
# Repeated builds: retain old character package; choose a NEW empty directory.
.\windows\build-character-pair.ps1 -PersonalUseOnly -MaleCharacterOutput artifacts/male-character-v4-next
```

Individual developer assets:

```text
python tools/build_neural_studio.py --appearance-v4 --output artifacts/v4-female
python tools/prepare_makehuman_male.py --appearance-v4 --output artifacts/v4-male-character
python tools/build_neural_studio.py --character artifacts/v4-male-character --output artifacts/v4-male
python tools/character_studio_server.py --female artifacts/v4-female --male artifacts/v4-male
node tools/smoke_renderer_lease.cjs http://127.0.0.1:8080
node tools/inspect_authored_appearance.cjs http://127.0.0.1:8080
```

Use the port actually printed by the server. Authoring requires the pinned
build-time NumPy/Pillow/SciPy environment. Assets are generated at build time and
included locally, not generated/downloaded by the runtime. Enhanced assets are
explicitly rejected by native packaging/server setup; default stock preparation
still supplies the separately tested native path. Existing EXEs require rebuilding.

### What the render checks do and do not show

The browser check captures neutral, full-blink, PP, FF, open-vowel and tongue-control
poses for each sex; verifies authored maps, 66 source face controls and hair
material handling; and runs balanced off/on/on/off wrap timing blocks. These are
held diagnostic controls, **not independent phonetic annotations**.

Visual review exposed scalp intersection in the first analytic hair shell; the
replacement projects onto actual head triangles and the new render removes that
intersection. Brows remain stylized/coarse. **Full-blink frames still show small
eye gaps**, so eyelid/contact quality is not accepted. Lip/teeth/tongue contact and
transitions need independent reviewed landmarks/reference and further tuning.
Do not hide eyes/teeth or call these quality checks complete merely because a
pose renders. `holdDiagnosticPose()` and bounded `diagnosticVertices()` are
capture-only inspection APIs, not playback emotion inference.

Timing is software SwiftShader at 256px including synchronous readback/JPEG,
with warm-up excluded; it is not GPU-only timing, interactive FPS or an i5 report.
Noisy off/on results cannot establish an improvement or hardware overhead bound.
Keep wrap off by default pending target-hardware testing. Exact local results
are in [the render receipt](evidence/realism-v4-render.json).

New actual CPU-synthesized talking previews: [male](../docs/media/realism-v4-male-talking.mp4) (am_michael, 2.048s, 31 frames) and [female](../docs/media/realism-v4-female-talking.mp4) (af_heart, 1.7493s, 27 frames). Same text, “Mama brought five blue bags.” Each uses its own newly generated WAV/transcript-bound cues; all encoded frames and media streams decode successfully. [Male receipt](evidence/realism-v4-male-talking.json), [female receipt](evidence/realism-v4-female-talking.json). These are fixed-audio-clock offline exports, not physical output measurements, independent phonetic reference or real-time playback performance. The optional original-material comparison in the capture tool uses the same v4 geometry/maps, not an older v3 asset.

## Hosted checks and preserved failure

At runtime source `c5c89ea`, the enhanced male Windows EXE/selector/installer job [passed](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39027883450). The [core run](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39027883429) passed 11/12 jobs, including enhanced Linux appearance/lease rendering, but Windows file:// playback timed out waiting for audio progress. [Failure evidence](evidence/realism-v4-first-core-failure.json) is preserved; the original cause is not proven. The follow-up observes actual decoded-media time and played ranges inside the page with a bounded event trace, rather than a later RAF poll. This harness passes locally on the previously accepted offline package; that is not a reproduction of the failing Windows environment or a physical measurement. Fresh hosted checks at source `7cf2cda` are **running**, not yet accepted: [core](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39029288358), [male Windows](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39029288339). The runtime viewer bundle remains `e6007d4…`; the follow-up changes the test observer/docs, not the app rendering. No assertion that the first run was green.

## Independent phone-reference intake

```text
python tools/check_independent_reference.py --manifest PATH/manifest.json --make-template --output reference-template.json
# Independently annotate that exact WAV, fill provenance and phones in the template.
python tools/check_independent_reference.py --manifest PATH/manifest.json --reference independent-reference.json --output reference-comparison.json
```

Phone records are `{"phone":"P","start":0.5,"end":0.7,"uncertainty_ms":15}`.
These numbers illustrate the schema only; **they are not a supplied reference**.
Use measured times from the bound WAV, not these numbers. Current diagnostic
classes: P/B/M, F/V, L, W/UW, AA and SIL; other phones are not invented/scored.
Manual annotation or a genuinely separate aligner must identify method/tool,
annotator/model and source. External aligners also identify a 64-digit model hash.
Known Rhubarb/Sphinx-family references are rejected for this intake. A provenance
declaration is not independently audited truth. Acoustic and visual boundaries
need not coincide. The tool reports estimated-class coverage/onset differences;
it never silently retunes, certifies mesh contact or approves human quality.
**No genuine independent annotation has been supplied or accepted yet.**

## Physical display/speaker offset

Open **physical AV capture probe** in the studio footer. At comfortable low volume,
record the flashing rectangle and actual speaker with a camera/microphone sharing
one recording timeline. Three 1200 Hz tone/flash markers are scheduled against
WebAudio time. Scheduling/callback metadata is **not** actual output latency.

```text
python tools/measure_recorded_av.py --recording private-camera.mp4 --roi X Y WIDTH HEIGHT --physical-recording --output observed-offset.json
# Only if capture-device calibration is independently established:
python tools/measure_recorded_av.py --recording private-camera.mp4 --roi X Y WIDTH HEIGHT --physical-recording --capture-offset-ms OFFSET --capture-uncertainty-ms UNCERTAINTY --output corrected-offset.json
```

ROI is the camera-video pixel rectangle tightly enclosing the black/white marker,
not the whole screen. Local MP4/MOV/WebM ≤128MiB; processes at most the first 30s.
FFmpeg preserves common presentation timestamps, including audio-track start
offsets; bounded video ROI and 48kHz mono audio decode, 60s command timeout.
Positive offset means recorded sound is later than recorded light. Needs matching
3–20 markers and stable offsets; ambiguous detections fail rather than silently
matching/dropping markers. The report includes frame/audio quantization lower-bound
uncertainty. Calibrate capture-device AV sync and microphone/acoustic path delay;
source/calibration declarations are not automatically verified. Nothing uploads.

Synthetic software fixtures correctly recover +120ms and a +100ms container-track
shift, but **are not physical measurements**. Screen recordings/loopback cannot
certify display/speaker output either. No actual physical recording, corrected
laptop latency, i5-U/16GB whole-app memory/thermals or personal data-recovery report
has been supplied. All remain open acceptance items.
