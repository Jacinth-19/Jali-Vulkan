# Character calibration, performance, appearance and export

Implemented for the current detailed head. Local checks: **132 Python / 31
JavaScript tests**, real-head Chromium controls and an actual WebM with both audio
and video decoded by FFmpeg. The local UI transport/encoder fixture is explicitly
**non-speech**, not neural synthesis or perceptual approval. Hosted Linux/Windows genuine
speech, native and personal frozen-app regressions passed: **all 11 jobs green**
in [run 38945207804](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38945207804), implementation
`d4743f3e5b45d389c7f086f9ea59995dcf0d19cd`. [Hosted evidence](evidence/creative-upgrades-actions.json)
and [local checks](evidence/creative-upgrades-local.json) retain exact scope and
prior failures. Human/laptop acceptance remains separate.

After updating source, rebuild the prepared frontend, then start the launcher:

```powershell
npm.cmd ci --prefix tools --ignore-scripts
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
- **Export synchronized WebGL video:** offline VP8/Opus WebM at the timeline
  FPS and selected 256/512/768-pixel quality resolution. Each video frame samples
  the same source-WAV media clock as the exported weights. Rendering speed only
  changes how long export takes, not the animation clock. The WAV bytes are
  re-checked against both audio/cue SHA-256 identities before decoding. Audio is
  resampled to 48 kHz and encoded as Opus, **not byte-identical PCM**. Settings,
  audio transport and canvas interactions lock while exporting. Cancel discards
  incomplete output; successful completion offers explicit movie/frame downloads.

`recorded-frames.json` uses **jali-recorded-frames-v2**, mode
`offline-fixed-media-clock`: one row per submitted encoded video frame with its
media time, layered weights, head/eye angles, source identities and settings. The
animation JSON additionally includes the exact clip-end rest sample; video uses
frame starts strictly before that endpoint. Opus codec delay/padding and final
video-frame padding may affect container duration. This is **not physical AV
certification, bit-identical audio, MP4, or universal DCC retargeting**.

Current Chrome with WebCodecs and a secure context (HTTPS or localhost) is
required for video. Frames cross into the encoder as CPU-owned RGBA rather
than shared GPU textures; encoder queues are bounded, stalled flushes time out
after 15 seconds, and Cancel also interrupts a pending encoder flush. Unsupported
encoders fail explicitly; JSON/CSV still work.
Native supports facial timelines, but video and appearance are WebGL-only.
The pinned MIT webm-muxer license is included in prepared studio assets. No
runtime network service, recorder extension or FFmpeg install is required.

The earlier live MediaRecorder approach was replaced after a Linux genuine-speech
CI timeout and reproducible zero-byte repeat/partial captures. The regression
suite now checks repeated complete exports, exact pose/time agreement with the
fixed-clock timeline, cancellation without stale downloads, and FFmpeg decoding
of both streams and every expected decoded frame. Browser security stays enabled.
A separate hosted Linux GPU-frame encoder stall led to CPU-owned frame handoff;
controlled tests also exercise cancellation and timeout of an encoder that never
flushes. Local genuine stock-Kokoro speech export also passed (1.792 s,
54 frames at 30 FPS). The final full genuine-speech protocol also passed locally
with browser security enabled, CPU-owned frames and all 104 frames decoded for
a 3.46-second clip. These are not listening-quality approvals.

## Remaining acceptance

Human review of eyes, lip/teeth contact, expression balance and materials; measured
target-i5 throughput and physical AV synchronization; broad reverse-DCC round trips;
and the existing signed-release/redistribution/legal gates remain open. No paid
service, microphone, model training or automatic emotion inference was added.
