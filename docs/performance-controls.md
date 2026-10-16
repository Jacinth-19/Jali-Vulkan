# Performance controls and native palette implementation

This increment implements concrete M4/M5/M6 foundations. **It does not finish
all outstanding milestones.** The detailed MPFB head remains WebGL-only.

## Cancellation and recovery (whole-utterance generation)

The studio has **Cancel generation** and **Stop playback / reset face** buttons.
Cancel applies to a running generation/analysis job; Stop applies to playback.
The backend still completes an utterance before playback. It does not advertise
sentence batching, incremental neural inference or a streaming chunk protocol.

- `POST /api/cancel` accepts exactly `{"id":"<32 lowercase hex job ID>"}`.
  It uses the same same-origin/`X-Jali-Token` checks as generation. These checks
  prevent browser CSRF; they are not remote-user authentication.
- Known running jobs return HTTP 202 with `state: cancelling`. Repeated cancel
  requests while cancelling are idempotent. Unknown jobs return 404; malformed
  requests return 400; ready/error/cancelled jobs return 409.
- A job-owned cancellation token wraps both the fresh CPU speech worker and the
  Rhubarb analyzer. It terminates/kills and reaps only its current child. No
  process-name-wide kills are used. Subprocess timeout/error remains distinct
  from intentional cancellation.
- The worker slot remains busy until child cleanup and output cleanup finish.
  Partial/cancelling/cancelled media is never published through `/sessions/`.
  Cancelled/error job records share the bounded six-record retention list.
- Ready publication and cancellation share the state lock: cancellation cannot
  turn an already-ready clip into a permanently-cancelling record. Ready clips
  are immutable; use Stop if a request has already completed.
- Cancel/failure returns the browser to a neutral face. Stop removes the current
  audio source, clears speech/style/gaze and verification/download selection,
  without deleting the bounded replay history.

## Deterministic expression/gaze arbitration

`web/neural-head/performance.mjs` composes **speech**, **expression**, **procedural
blink/head motion**, and **manual gaze** separately, with bounded weights/angles.
Warm smile/cheek weights are reduced proportionally during closure, F/V and
rounding. At the full mapped A/E/F/G poses those warmth weights are zero.
The real browser test compares full-closure PNG pixels with neutral/warm styling
and requires equality. This protects that specific layering contract; it is not
an independent pronunciation or lip-contact quality assessment.

Forward/left/right/down gaze drives the actual `LeftEye`/`RightEye` bones, without
adding eight more active morphs to every shader loop. It is bounded to 0.08 rad
horizontal / 0.06 rad downward head-relative offsets from each eye's rest quaternion. Repeated
seeks do not accumulate rotations. It is a manual head-relative offset, **not**
camera tracking, attention detection or inferred intent. Forward resets to rest.

The existing small head drift and deterministic blink remain cosmetic and can be
disabled. Neutral/warm/attentive styles are explicit user choices, not learned
emotion or emotional speech-prosody control. Evaluated gaze targets, richer
speech gestures and naturalness review remain open.

## Native palette: 64 → 128, without truncation

`kMaxCharacterJoints = 128`, with a 256-node import bound. `JointPalette` is shared
by the importer, CPU reference and Vulkan pose uploader. The GLSL pose contains
128 matrices followed by the morph vector: **8,208 bytes**, morph offset **8,192**.
C++ static assertions and actual GPU comparisons check the layout. Device uniform
and storage-buffer limits are checked before mesh allocation. Compute workgroup
size stays 64; it is unrelated to joint capacity.

Generated 67- and 128-joint GLBs bind actual vertices to joints 66 and 127, not
merely append unused bones. Real Vulkan tests compare three poses against CPU
positions within `2e-5`; both GLBs pass the official validator with zero warnings.
The malformed importer suite also rejects a palette over 128 joints.

This removes the old 67-joint **capacity** blocker. It does not add MPFB's multiple
meshes/skins, 66 named targets, textures/materials, quantized/Meshopt decoding or
shared neural-session native rendering. The static rig audit reads the actual
capacity constants and continues to report those remaining incompatibilities.

## Evidence and remaining milestones

Local validation: **94 Python tests, 15 JavaScript tests, 11 native CTest entries**,
and the real new-speech/browser review (three recordings, 22 sampled poses, nine
estimated classes). Hosted Linux/Windows CI is being rerun for this source change;
see the project tracker/evidence update for the final hosted outcome.

Still open: independent articulation labels and validated rig tuning; full rich
native character/material/morph support; true bounded incremental playback;
reviewed expression/gaze/gesture quality; consumer Windows packaging; measured
physical target-laptop performance/AV sync; broader asset QA. The user reports a
successful Windows PC run, which is functional confirmation, not those measurements.
