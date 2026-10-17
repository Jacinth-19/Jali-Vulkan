# Eye/hair materials, additional characters and talking preview

## Scope

This is a **WebGL material upgrade**, not Epic MetaHuman integration or a
photorealism approval. Native keeps calibration, authored performance and weight
timelines; its appearance is unchanged. Browser video export requires current
Chrome. Human quality review, physical AV measurements and measured i5 performance
remain open. Existing portable EXEs do not change in place: rebuild them.

## Implemented treatment

`web/neural-head/surface-materials.mjs` uses Three.js physical materials on an
explicit allowlist of the known MakeHuman and Ready Player Me eye/hair materials.
Unknown imported materials are not guessed from loose name matching.

- Eyes: preserve original iris/sclera texture and skinning; dielectric IOR 1.376,
  clear wet coating and environment/direct-light highlights. The eye roughness
  slider still works. This approximates a wet surface; it does **not** add a
  refractive corneal shell, iris parallax/caustics, tear meniscus or eye occlusion.
- Hair: keep the MakeHuman ponytail's textured cards, alpha cutoff and geometry;
  add a UV-tangent anisotropic highlight, restrained tinted specular/sheen and
  MSAA alpha coverage where supported. Single-pass double-sided cards avoid an
  extra backface draw. FXAA alone is not multisample coverage.
- Budget: no new textures, strands, meshes or draw calls; hair gets one tangent
  attribute (16 bytes per existing hair vertex). Shader work increases and has
  **not been measured on the target i5**. It cannot turn coarse cards into a groom.
- `?surface=original` disables this material replacement for comparison. Diagnostics
  report applied eye/hair counts, tangent bytes and shading version. Render-asset
  metadata records the shading version, separately from the source mesh hash.

## Hair-Renderer-X review

Reviewed [Jacinth-19/Hair-Renderer-X](https://github.com/Jacinth-19/Hair-Renderer-X)
at commit **ff0b40347733d4b58ed334ffc45e158bebcdf4d3**:

- Its README describes a WIP Windows Vulkan strand renderer and Unity Enemies
  pipeline, requiring Vulkan SDK, CMake and Git LFS. This is not a WebGL plug-in.
- `fast_hair_strand_epic.glsl` expands strand segments into camera-facing quads
  using SSBO/index buffers and nonuniform descriptor indexing.
- `epic_hair_BSDF.glsl` contains R/TT/TRT, absorption/melanin and scattering
  machinery. Other passes prepare hair LUTs, voxelization and scattering. These
  require an actual groom/strand representation, unlike our ponytail cards.
- `resources/models/straight.hair` is an LFS pointer to 15,000,128 bytes;
  the neural hair examples also use external LFS assets. Their filenames and
  publication do not establish permission to copy/relicense them.
- No top-level LICENSE was found. `ext/Vulkan-Engine/LICENSE` is MIT, copyright
  Antonio Espinosa Garcia (2023), but that does not blanket-license all root
  application code or third-party grooms.

**No shaders, engine code or groom assets were copied.** The material changes here
are original configuration of Three.js features, not an implementation of Unity's
Enemies method or the repository's full strand/scattering pipeline. A future native
port needs a licensed groom, explicit strand/voxel/memory budgets, new Vulkan passes,
anti-aliasing/occlusion tests and target-device measurements. None is claimed done.

## Additional personal-use character

A separate **Ready Player Me brunette** sample is explicitly pinned to TalkingHead
commit `2afe6d79779313db8909badebf46f9805a6c7b70`:

- Source SHA-256: `8864c504b5c11daa2f0037afffdc0815bb0fa2e6062e37a584746116a3c2f538`.
- Upstream README attributes the sample to Ready Player Me under **CC BY-NC 4.0**.
  Attribution: Ready Player Me / met4citizen TalkingHead. Retain the source README
  and [license reference](https://creativecommons.org/licenses/by-nc/4.0/).
- This is **not CC0**, not an Epic MetaHuman, and not commercial/public release
  approval. It is an optional, explicit personal-noncommercial setup operation,
  never a runtime download or an automatic addition to the default EXE.
- Preparation deduplicates/prunes unused resources (17 source textures -> 11),
  without loosening the importer's 16-texture bound. The canonical package passes
  glTF validation: 8,026 vertices / 13,317 triangles, all 13 required speech/blink
  channels plus supported expression mappings. Source/normalized/package hashes
  and reusable retarget profile are retained beside the package.

```powershell
.\.venv\Scripts\python.exe tools\prepare_character_sample.py --personal-noncommercial
.\.venv\Scripts\python.exe tools\build_neural_studio.py --character artifacts/brunette-character --output artifacts/brunette-studio
.\.venv\Scripts\python.exe tools\neural_studio_server.py --assets artifacts/brunette-studio --bind 127.0.0.1 --port 8083
```

The Avaturn sample was inspected as a candidate, but its provider terms and exact
asset rights need review before adding an automatic installer. No Epic MetaHuman
assets have been obtained. Supply an authorized export to evaluate its rig,
textures and conversion requirements; DNA/grooms are not canonical GLB. The
current importer still requires explicit mappings, self-contained GLB and its
published geometry/texture budgets. Different prepared studios are separate;
profiles still share one active mesh per studio.

## Actual talking preview and EXE rebuild

With the stock studio running on loopback:

```powershell
node tools/capture_talking_preview.cjs http://127.0.0.1:8082
```

Developer prerequisites include the pinned Node browser tools and `imageio-ffmpeg`.
The tool submits new text to local CPU speech, verifies the actual WAV/text/cue
binding, renders 512-pixel frames at 15 FPS using that WAV clock, and encodes an
MP4 with the same speech. Output `artifacts/talking-preview/talking-face.mp4`,
`before.png`, `after.png` and `evidence.json` are actual rendered evidence, not
image synthesis. MP4 audio is AAC encoded; the source WAV hash is retained.
This offline developer MP4 path does not add FFmpeg to the personal runtime.

For the stock head, rebuild portable EXE and optional installer on Windows:

```powershell
.\windows\build-portable.ps1 -PersonalUseOnly -IncludeNativeVulkan
.\windows\build-personal-installer.ps1 -PersonalUseOnly
```

For the additional imported character, use the direct custom WebGL packaging
sequence in [workspace upgrades](workspace-upgrades.md#6-personal-installer-and-release-boundaries),
not the wrapper that deliberately prepares the stock head. Neither existing EXEs
nor an already installed copy update themselves. Signing stays optional; public
redistribution/source/license clearance remains blocked.
