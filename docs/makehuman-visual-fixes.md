# MakeHuman mouth, lighting and fiber cleanup

## First visual-fix batch — 2026-10-17

This follows the [decoded-preview review](makehuman-visual-review.md).
WebGL surface version **physical-oral-skin-fibers-v3**:

- **Mouth:** diagnostic mesh isolation confirmed that the tongue contributes most
  of the bright pink area; hiding it also reveals a brightly lit inner body surface.
  The fix preserves geometry, morph targets, bones and viseme weights. It attenuates
  oral lighting by each vertex's rest-space front/back depth, carried through
  existing skinning/morphs: tongue 0.025–0.375, teeth 0.4–0.95. This is an explicit
  lightweight cavity-light **approximation**, not ray-traced AO, cast shadows or
  corrected tongue anatomy. Oral contact/placement still needs human review.
- **Teeth:** retain texture, use restrained linear ivory tint, roughness 0.38,
  specular intensity 0.2 and environment intensity 0.12 instead of bright white
  default illumination. Teeth and tongue stay visible; nothing is hidden to fake
  a darker cavity.
- **Skin lighting:** the soft preset previously used key/rim/fill intensities
  1.3/0.6/1.7. New values are 1.6/0.5/0.35, allowing more facial form instead of
  dominant fill. Studio is 1.8/0.75/0.5; dramatic 2.5/0.7/0.22. No darkening or
  recolouring of skin albedo. Existing skin detail/roughness controls are retained.
- **Brows/lashes:** known shared fiber materials get dark-brown rather than pure
  black response, roughness 0.88, specular intensity 0.05 and environment 0.12.
  This reduces fiber glints/contrast. **It does not replace sparse/coarse geometry**;
  stippling and silhouette limitations remain. Hair geometry is unchanged.

No new meshes, draw calls, shadow maps or additional textures relative to v2.
The oral attribute adds **18,988 bytes** for the prepared stock oral meshes
(4 bytes per vertex). Existing skin detail still uses one 128² RGBA texture
(65,536 base bytes / approximately 87,380 including mip levels); existing hair
requires tangent data. Unknown materials and unsuitable oral geometry fall back
without modification. `?surface=original` preserves original materials **and**
original lighting presets; that mode is not the preceding v2 renderer.

## Same-recording comparison, with strict identities

The comparison reuses the two **actual previously synthesized stock CPU WAVs**,
not newly generated audio and not non-speech fixtures. Same camera, exposure,
roughness controls, low LOD and 15 FPS fixed clock. Old encoded v2 movies provide
the before frames. New v3 movies provide after frames.

A changed viewer hash correctly invalidates old runtime session/rig bindings.
**No runtime checks were relaxed.** `tools/run_surface_replay.py` is an explicit,
developer-only comparison server limited to the **two checksum-pinned public
recordings** from the previous preview evidence. It validates source WAV/text/cues,
requires every rig field except viewer identity to stay identical, checks the
new viewer/model bytes, writes a fresh session with source-manifest/old-rig
provenance and validates the new binding. It refuses synthesis. It is **not** an
archive migration feature or permission to replay arbitrary old user sessions.
Metrics retained from the old session describe the original recording, not a new
speed benchmark. Back up user data and retain old builds for old archives.

Explicit developer flow (use original verified session directory):

```sh
.venv/bin/python tools/run_surface_replay.py --character female \
  --source-session ORIGINAL_FEMALE_SESSION_DIRECTORY \
  --assets artifacts/visual-fixes-female-studio \
  --sessions artifacts/visual-fixes-female-sessions --port 8084
# Server prints its fresh comparison_session ID. In a separate terminal:
JALI_PREVIEW_SESSION=PRINTED_COMPARISON_SESSION_ID \
  node tools/capture_talking_preview.cjs http://127.0.0.1:8084 artifacts/visual-fixes-female-preview
```

For the male use the male prepared studio, `--character male`, a different session
store/port and `JALI_PREVIEW_VOICE=am_michael`. Build the studios explicitly with
`build_neural_studio.py --output ...` (female) or additionally
`--character artifacts/male-character` (male). These environment-variable examples
use POSIX syntax; Windows PowerShell uses `$env:NAME='value'`.

Original WAVs are ignored session data, not committed assets. If those sessions
have been removed, the MP4's lossy AAC audio cannot recreate their exact WAV
hashes: make a **new baseline and after** comparison rather than claiming equivalence.

## Validation and remaining scope

Local **149 Python / 40 JavaScript tests pass**, including role allowlists, oral
attribute bounds/fallback, unchanged geometry/material texture/alpha contracts,
lighting fallback and rejection of non-viewer rig changes. Actual shader renders
are being verified on both prepared characters. Hosted CI and final comparison
receipts are pending this runtime revision's run; the prior checkpoint is not
acceptance of this new shader.

This is not a complete facial asset overhaul. Lip-corner/rounding geometry,
full-blink seal and F/V contact, better brow/lash/hair assets, authored skin detail,
physical AV, listening/human approval and measured i5-U/16 GB performance remain
open. No scanned skin, subsurface transport or full strand scattering is implied.
Appearance/video remain WebGL-only; native geometry/weights are unchanged.
Existing personal EXEs need rebuilding; signing remains optional. Default hosted
Windows packaging tests use the female asset, not a separate custom male EXE.
