# Actual rendered talking preview

`makehuman-talking-preview.mp4` is a small, public synthetic demonstration:

- Actual CC0 MPFB/MakeHuman head from the pinned TalkingHead asset; attribution and
  source in [the appearance guide](../eyes-hair-characters.md).
- Newly synthesized local stock Kokoro `af_heart`, not a clone, microphone recording
  or Arena voice-00. No model weights or personal input are included.
- 512 × 512, 15 FPS, 7.104 seconds / 107 frames. Offline WebGL render synchronized
  to that session's source WAV clock, encoded to H.264/AAC MP4.
- Script: “Hello. Here is our updated local character. Watch the eyes and the hair
  as I speak. Please bring my blue paper bag.”
- [Identity, hashes, material budgets and limits](../evidence/eye-hair-preview.json).

This is not AI image generation, strand-hair/MetaHuman quality approval, physical
AV verification, native appearance parity or an i5 performance benchmark. The
additional noncommercial character's private local review movie stays in ignored
`artifacts/brunette-preview/`; no model or third-party groom is committed here.

## Male/female skin previews (2026-10-17)

`makehuman-female-skin-talking.mp4`: 107 verified encoded frames, 7.104-second
24 kHz mono stock Kokoro `af_heart` WAV. `makehuman-male-skin-talking.mp4`:
120 verified encoded frames, 8.000-second stock Kokoro `am_michael` WAV.
Both: actual local CPU speech, text-derived estimated cues and WebGL renderer;
512×512, 15 FPS, H.264/AAC, offline fixed-WAV-clock capture. Not generated imagery.
Both streams decode; frame counts verified by FFmpeg framemd5, no `-shortest`
frame loss. [Exact WAV/text/rig/video identities and pose traces](../evidence/makehuman-skin-preview.json).

CC0 MakeHuman/MPFB/TalkingHead assets; male uses official MPFB 2.0.15 gender
targets with refitted rig/eyes. Shared original outfit, ponytail and base textures.
Skin detail is procedural, not scanned or subsurface scattering. Voice/model
notices remain those of the prepared local Kokoro stock setup; no cloned user
voice. [Source hashes, setup and rights scope](../makehuman-male-skin.md).
This is not Epic MetaHuman, target-i5 performance, physical AV or final human
quality approval. Appearance/video changes are WebGL-only.
