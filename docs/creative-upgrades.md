# Character calibration, performance, appearance and export

Implemented for the current detailed head. Local checks: **132 Python / 29
JavaScript tests**, real-head Chromium controls and an actual WebM with both audio
and video decoded by FFmpeg. The local UI transport/encoder fixture is explicitly
**non-speech**, not neural synthesis or perceptual approval. New hosted genuine
speech, native and packaged regression checks are pending. Earlier all-green
upgrade evidence does not certify these new changes.

After updating source, rebuild the prepared frontend, then start the launcher:

```powershell
.\.venv\Scripts\python.exe tools\build_neural_studio.py
.\windows\launch-studio.cmd
```

Rebuild existing personal portable EXEs too; no runtime model downloads are added.

## 5. Named character calibration profiles

Adjust jaw, lip closure, contact, rounding, tongue and transition sliders; enter a
name under **Character profiles**, then Save. Load/Delete work without editing
code. Up to 20 named calibrations live in browser local storage per model SHA-256;
Export/Import moves a JSON profile book between browsers. Imports must match the
character rig and pass strict bounded validation. Import replaces that rig's book;
export a backup first. Browser data clearing removes local profiles. This is not a
new multi-character importer: each supported loaded character has its own scope.

## 6. Eyes and idle

Enable **Natural idle / smooth gaze** for irregular, deterministic blinks (with
occasional double blinks), eased manual gaze changes, adjustable eye contact and
restrained layered head motion. Blink strength/tempo, head strength and gaze easing
are adjustable. Eye contact is an authored look-away amount, **not webcam tracking**.
The existing procedural-motion checkbox gates blinks/head motion. No selected
recording: natural idle uses a separate wall clock, without inventing audio/cues.
A paused selected recording freezes motion; seeking reproduces the media-time
pose. Legacy motion remains the default for old comparisons and low idle CPU use.
JS/Python layers are numerically parity tested and native uses the same settings.

## 7. Manual expression blending and sequences

Neutral, Warm, Attentive, Serious and Surprise are **manual styles**, not inferred
emotion. Intensity scales them; speech closures, F/V contact and rounding suppress
conflicting mouth expression weights. Add timed expression rows with start/end,
style, strength and fade. Overlaps add with bounded weights, not unconstrained
facial displacement. Maximum 32 events across 0–60 seconds; fades cannot exceed
half the event. Times use absolute paragraph time during batching and media time
on the combined recording. Invalid row edits do not replace the last valid state.
Export/import a manual-performance JSON to preserve motion settings and sequences.
Nothing analyzes sentiment or predicts the speaker's feelings.

## 8. Appearance

WebGL controls provide Studio/Soft/Dramatic lighting, exposure, skin and eye
roughness, five solid backgrounds and Portrait/Close-up/Three-quarter/Wide camera
presets. The existing PBR textures/environment and MSAA are retained; optional
FXAA adds a postprocess anti-aliasing pass. Camera orbit remains available.
These are real renderer settings, **not new photorealistic assets, a skin-scattering
shader or quality certification**. Native has its own fixed camera/material/light
pipeline; these appearance controls are explicitly disabled in native mode.

## 9. Reusable animation and video

Choose a completed verified recording (not an in-flight sentence chunk):

- **Animation JSON:** fixed media-clock samples at 15/24/30/60 FPS, named morph
  weights, head/eye angles, calibration, motion/sequence settings and WAV/text/rig
  identities. Reproducible independently of actual interactive frame drops.
- **Weight CSV:** the same zero-filled, named weight channels and angles. Angles
  are radians in the Jali rig coordinate frame. Download the original WAV alongside
  it; other tools may need coordinate conversion and retargeting. Not FBX/BVH or
  universal Blender/Maya import.
- **Record WebGL video from start:** captures the canvas and the selected WAV
  through a single media-element/Web Audio graph into WebM (Opus audio). Audio is
  encoded, not byte-identical to the WAV. Settings lock during capture. At finish,
  explicit download links provide the movie and its actual render-submission
  media-time samples. Finish capture permits an explicitly partial movie;
  pausing/seeking/rate changes or audio errors discard the interrupted capture.

Video is real-time browser capture, **not offline MP4 rendering or physical AV
certification**. Slow rendering can drop video frames. Its sparse actual-frame
JSON is distinct from the fixed-clock animation JSON; do not assume one row per
encoded video frame. WebM support depends on the browser (Chrome is tested).
Native can export facial timelines, but user video capture is explicitly WebGL-only.
The older developer offline MP4 capture tools remain available separately.

## Remaining acceptance

Human review of eyes, lip/teeth contact, expression balance and materials; measured
target-i5 throughput and physical AV synchronization; broad reverse-DCC round trips;
and the existing signed-release/redistribution/legal gates remain open. No paid
service, microphone, model training or automatic emotion inference was added.
