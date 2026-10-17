# Male MakeHuman and shared skin treatment

## Delivered scope

The male is a **MakeHuman gender-target variant** of our existing CC0 rigged
TalkingHead/MPFB character—not a renamed female asset or merely a different voice.
The pinned MPFB 2.0.15 adult male-minus-female targets change real geometry,
including jaw, brow, neck, shoulders and stature. The source's custom identity,
ponytail, outfit and base-colour textures are shared. This is **not** an independently
scanned/authored male, a new hairstyle, an Epic MetaHuman or final realism approval.

Build method: join all **11,779 body vertices** to the canonical MakeHuman OBJ
through exact UVs (V flipped, tolerance 0.000001); apply ancestry-averaged adult
and average-muscle/weight gender deltas in metres; transfer deformation to
attachments and facial target positions; recompute rest and morph normals.
**Refit joint positions and inverse binds**, keeping rest orientations. Rigidly
translate the spherical eyes with their refitted pivots. Keeping the old eye/head
pivots is incorrect because these targets also change stature. Facial target names,
all required speech/blink controls, eye bones and strict import limits are retained.
Human eyelid, teeth contact and expression review is still required.

### Skin on both characters

`physical-skin-eyes-hair-v2` replaces only the known `Human.body` material.
It retains the original base-colour texture and adds restrained dielectric
specular response (IOR 1.4, specular intensity 0.32, no clearcoat), less overpowering
skin environment fill (0.38) and subtle procedural micro-normal/roughness variation.
This is **not subsurface transport or scanned pores**; no claim of photorealism.

One deterministic, shared **128×128 RGBA detail texture / 65,536 base bytes** per
scene (about 87,380 bytes including GPU mip levels); repeat 24, mipmapping for
distance, normal scale 0.22. No new meshes/draw calls or runtime downloads. Authored
normal maps are preserved instead of overwritten. Original eye/hair coatings remain.
The appearance roughness slider still works. `?surface=original` bypasses all surface
upgrades for a controlled same-WAV/same-camera comparison. Original mode is the
original asset shading, not the preceding eye/hair-only revision.

## Explicit preparation (not startup)

Use the ordinary local studio dependencies, pinned Node tools and stock speech
setup first. See [local neural setup](../README.md) and the eye/hair guide.
Install the **build-only** extra, then prepare into an empty output directory:

```sh
.venv/bin/python -m pip install -r tools/requirements-male-build.txt
.venv/bin/python tools/studio_voices.py --install am_michael
.venv/bin/python tools/prepare_makehuman_male.py
node tools/test_makehuman_male.mjs
.venv/bin/python tools/build_neural_studio.py --character artifacts/male-character --output artifacts/male-studio
.venv/bin/python tools/neural_studio_server.py --assets artifacts/male-studio --port 8083
```

On Windows use `.venv/Scripts/python.exe` for those Python commands. SciPy 1.17.1
is geometry-preparation-only, not a new speech/runtime/EXE dependency. Blender is
not needed: the builder evaluates CC0 target *data*, not MPFB's GPL addon code.
The builder refuses to overwrite a nonempty character directory. Use a fresh output
name to rebuild; back up old rig-bound casts/conversations/archives first.

Default stock female preparation is unchanged:

```sh
.venv/bin/python tools/build_neural_studio.py
.venv/bin/python tools/neural_studio_server.py --port 8082
```

The two studios use separate session stores for developer comparisons. A packaged
studio still uses **one selected mesh, one audio player, one inference worker**;
this is not a live male/female mesh switcher or simultaneous two-avatar renderer.
Voice profiles share whichever mesh was prepared. The default voice remains
`af_heart`; choose `am_michael` in the male studio's voice/profile controls, and
`af_heart` for the female; neither is the auditioned personal voice.

## Personal Windows EXEs

Existing EXEs do **not** acquire changes automatically. The usual
`windows/build-portable.ps1` rebuild resets to the stock female. For a male
personal package, first prepare `artifacts/neural-studio` explicitly with
`--character artifacts/male-character --output artifacts/neural-studio`, then
use the existing `tools/package_windows.py --personal-build` flow described in
[Windows packaging](windows-portable.md). Retain the package's `licenses/`,
character manifest and provenance. Personal builds may remain unsigned.

Back up user data first. The compiled viewer hash participates in rig identity;
old casts/archives may be rejected after this appearance upgrade even when the
mesh itself is unchanged. Retain the previous build for verified old replay, or
explicitly recreate profiles/scripts. No identity checks were weakened.

## Actual rendered evidence

- [Female talking video](media/makehuman-female-skin-talking.mp4), stock `af_heart`.
- [Male talking video](media/makehuman-male-skin-talking.mp4), stock `am_michael`.
- [Capture identities/decoded-frame evidence](evidence/makehuman-skin-preview.json).
- [Male asset and target provenance](evidence/makehuman-male-asset.json).

These are actual local CPU speech + WebGL frame captures, **not generated images**.
512×512, 15 FPS offline fixed-WAV-clock rendering, AAC audio, H.264 video. Their
voices have different durations. Full FFmpeg video/audio decode and exact encoded
frame-count verification are required. Current Chrome is required for browser
video export; the developer MP4 helper additionally uses FFmpeg.

Human appearance/listening acceptance, physical AV offset and measured Windows
i5-U/16 GB performance remain open. This is WebGL-only appearance/video work;
native calibration, authored performance and weight timelines retain their scope.
No public release/redistribution clearance or full strand-hair pipeline is implied.

## Sources and rights retained

- CC0 TalkingHead MakeHuman asset, commit
  `2afe6d79779313db8909badebf46f9805a6c7b70`, SHA-256
  `63c645a2a863b9972e9a9c2ed576a1de4c390b8475508e1473e69c87a3ee299c`.
- MakeHuman Community MPFB **2.0.15**, commit
  `f4f4f1ffa8203585730a7ce433b66738777ba168`. Pinned archive SHA-256
  `af03a0f41f19806c717b0c832ddd6513b06fd6258228b5ab844e06792e2e72ac`.
  `LICENSE.ASSETS.md` explicitly CC0; addon **code** GPL3, not copied or executed.
  Eight target hashes/weights are retained in the generated provenance.
- Existing TalkingHead/MakeHuman outfit, hair and textures are shared unchanged;
  no Hair-Renderer-X assets, Epic assets or new scanned skin were imported.
- Build proof/stock recordings are public synthetic fixtures, not user voice data.
  Asset notices do not by themselves clear every dependency/model for distribution.

## Validation checkpoint

Local **146 Python / 37 JavaScript tests pass**. All **12 hosted jobs succeeded**
in [run 39017428466](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39017428466),
runtime `d78fc3ba92052ef33597d9183c712518bcd3e8ca`. Male generation, strict import
and actual browser workspace controls passed in job 117352319235. Stock Windows
frozen EXE rebuilding, clean-PATH execution and unsigned installer install/update/
uninstall passed in job 117352319734. The notice receipt explicitly retains
`redistribution_approved: false` and unsigned-personal signing status.
[Exact steps, Windows notice receipts and limitations](evidence/makehuman-skin-actions.json).

The **male custom Windows EXE was not separately exercised**. Hosted male browser
controls use explicit non-speech fixtures; the delivered local male/female movies
use actual newly synthesized CPU speech and verified estimated cues. Artifact ZIP
retrieval to this sandbox was blocked at the Azure redirect; no hosted/local male
binary hash equivalence is claimed. This does not replace the open human/AV/i5 gates.
