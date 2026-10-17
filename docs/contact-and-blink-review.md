# Brow/blink follow-up and contact review — 2026-10-17

## Implemented, not artistically certified

The enhanced **female and male WebGL** builds now have:

- 900 flow-varied tapered brow ribbons, skin-projected rest positions, per-vertex source skin/morph anchoring, and a feathered density underlay. This is still a procedural/stylized approximation, not scanned or artist-approved hair. The underlay adds **one asset primitive/draw and a 128×32 RGBA texture**; it is not a free runtime shader change.
- Separate `jaliEyeSealLeft/Right` additive targets. The source full-blink pulls parts of the lid behind the globe. The new targets move affected vertices toward the actual eye triangle surface plus 0.8 mm, with a strict 12 mm displacement cap. **Largest actual offsets: female 8.659 mm; male 6.418 mm. These are not submillimetre corrections.** Activation is smoothstep of the original blink from 0.7 to 1; rest and half blink receive zero correction. No blink gain above 1, eye hiding or eye scaling.
- Original body rest/normals and all **66 original body morphs** are hashed and asserted unchanged before compression. Enhanced body: 68 total / 66 source / 2 corrective controls; 28 retained runtime controls. Stock/non-ported rigs stay 66 / 26, with no automatic correction. Both explicit names **and our authored material marker** are required.

### Geometry audit — limited, not a visibility/quality certificate

| Full source-resolution frontal geometry | Original full blink | Corrected full blink |
|---|---:|---:|
| Female: exposed eye-depth samples / 1,924 | 214 | 0 |
| Male: exposed eye-depth samples / 1,924 | 242 | 0 |

This is a **1 mm model-space orthographic grid**, with 0.05 mm depth tolerance, including triangle backfaces. The post-authoring audit shares its intersection helper with the authoring code: **not an independent implementation or reviewer**. It can miss sub-grid slivers and does not certify culling, texture waterlines, continuous collision, gaze combinations, every view, LOD or anatomy. Actual renders still have conspicuous pale lid margins and stylized lashes/brows; do not interpret “0 samples” as final artistic acceptance.

`tools/inspect_eye_clearance.cjs` additionally captures **32 actual WebGL frames**: both sexes × full/low LOD × neutral, half, original full-blink bypass, corrected full blink, left-only, right-only, held gaze and three-quarter closure. It asserts the loaded LOD/hash, bounded corrective activation, diagnostic bypass reset and rendered ray/barycentric sampling consistency. These are inspection frames, **not an automated pixel verdict**. The first local attempt failed when the single-process test browser closed after its last context; fresh browser lifecycles per model/LOD pass.

## Independently supplied contact landmarks

The new tool samples **actual rendered, morphed/skinned vertices**, not rest positions or inferred audio cues:

```sh
node tools/check_contact_reference.cjs \
  --url 'http://127.0.0.1:8082/characters/male/?lod=full' \
  --make-template --output /your/private/contact-template.json
```

This writes an **unfilled** exact-GLB/LOD-bound template and mesh/control/index layout. No anatomical landmarks or contact thresholds are invented. In a paused studio's developer console:

```js
JaliHeadDemo.setCaptureMode(true, 768);
JaliHeadDemo.holdDiagnosticPose({viseme_aa: 1});
// Coordinates normalized over the canvas, not the whole page.
JaliHeadDemo.pickDiagnosticLandmark(0.5, 0.6);
```

Picking returns a rendered triangle's mesh, vertex indices, barycentric weights, world point, pose and exact model SHA. **A human must identify the anatomy** and record the method/source/reviewer. A visible point chosen in an open pose can then be measured in a different held pose of that same GLB. This is not automatic lip/teeth/tongue landmark identification. Reset with `JaliHeadDemo.setCaptureMode(false)`.

Populate the template with cases containing `id`, bounded source `pose`, and `pairs`. Each pair has `id`, `a` and `b` anchors (`mesh`, `vertices:[{index,weight}]`), `metric:'distance'`, and declared `min_mm`/`max_mm`. A vertex uses one weight of 1; a triangle uses three nonnegative weights summing to 1. `signed-separation` additionally needs a unit `normal` in the rendered model-world axes. Signed point separation is **not** a surface penetration test. Externally supplied three-vertex weighted anchors are not checked for triangle membership; the rendered picker returns an actual hit triangle.

Review at least PP lip closure, FF upper-incisor/lower-lip placement, open vowel clearance, and the intended tongue/palate or tongue/teeth landmarks. Suitable anatomical criteria, reference phonetics and tolerances must come from the reviewer, not the same synthesis/viseme pipeline.

```sh
node tools/check_contact_reference.cjs \
  --url 'http://127.0.0.1:8082/characters/male/?lod=full' \
  --reference /your/private/reviewed-contact.json \
  --output /your/private/contact-measurements.json
```

Inputs are bounded (1 MiB, 24 cases, 128 pairs), with exact GLB SHA/LOD, known controls, finite weights and valid mesh indices required. Corrective controls cannot be manually substituted for source poses. Existing output files are refused unless `--overwrite-output` is explicitly supplied; the reference itself remains protected, including symlinks/hardlinks. The output reports mm distances, supplier-declared ranges, provenance and reference SHA. Even a pass keeps **independent-review verification, human quality acceptance, phone timing verification and physical AV false**. Reviewer identity and independence cannot be verified by this tool. There is **no real independent contact reference supplied yet**.

`tools/test_contact_browser.cjs` exercises the full template/intake/rendered-sampling path with **arbitrary neighbouring vertices, explicitly marked synthetic and requiring `--allow-fixture`**. Its results are only a transport regression, never anatomical/contact approval.

## Physical AV: still needs an actual recording

The existing `av-probe.html` and `tools/measure_recorded_av.py` remain available; see [commands and calibration limits](realism-v4-and-reference-validation.md). **No physical AV number has been measured in this follow-up.** Browser audio clocks, encoded talking videos and synthetic shift recovery cannot substitute for recording the screen and actual speaker together.

Next input: a phone/camera video showing the probe rectangle and capturing speaker tones, plus frame rate/device details and any camera AV calibration. Use a comfortable volume, keep the rectangle unobstructed, and specify whether Bluetooth is part of the target setup. Preserve the original recording/PTS; do not export an edited copy with unknown track offsets. Camera latency, sound travel, frame quantization and calibration uncertainty must be reported. Without calibration, report observed camera-recorded AV offset, not certified absolute PC latency.

Independent phonetic reference, final artistic/contact approval, actual i5-U/16 GB whole-app RAM/thermals/smoothness and personal install/recovery acceptance remain **OPEN**. Signing stays optional; redistribution remains separate. Enhanced appearance/correctives are WebGL-only, not a silent native port. Old recordings stay bound to their original model/viewer bytes.

## Validation and evidence

- Local regression: **162 Python / 54 JS passed**.
- Both enhanced builds/import/LOD audits, selector/unload/scope checks, real same-profile cross-tab lease checks, held contact poses, shader/wrap checks, synthetic contact transport, and both-LOD eye inspection passed.
- [Bound geometry/render receipt](evidence/brow-blink-contact-local.json). New actual CPU-speech previews, if linked there, have fresh rig bindings; they do not provide independent contact or physical AV truth.
- Previous source `7cf2cda`: **12 core + 1 male Windows jobs successful**, [completed receipt](evidence/realism-v4-followup-actions.json). This is historical acceptance, not a result for these new changes. Current runtime source **0b307c6** also passed **all 12 core + 1 dedicated male Windows jobs**: [completed receipt](evidence/brow-blink-contact-actions.json). This includes fresh enhanced EXE/selector, clean-PATH actual speech, benchmark and unsigned installer automation. Binaries were deliberately not publicly uploaded; proof artifact download was blocked by the sandbox network redirect, so no separate downloaded package/hash claim is made. Build personally in a fresh checkout with `windows/build-character-pair.ps1 -PersonalUseOnly` after explicit setup; retain old packages and user-data/profile backups. Hosted installer checks are not the user's personal install/recovery acceptance.
