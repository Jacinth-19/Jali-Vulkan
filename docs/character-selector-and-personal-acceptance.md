# Male Windows package, character switching and remaining acceptance

## Requested six-area follow-up — 2026-10-17

This is an incremental delivery, **not a claim that all six areas are finished**.

| Area | Current scope |
|---|---|
| 1. Male Windows EXE | Dedicated hosted workflow added: actual male-default frozen EXE, SHA-checked male asset, clean PATH, new CPU speech, both characters, integrity/tamper checks and unsigned installer. **Passed** in corrected run [39024328601](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39024328601). [Exact notice/step receipt](evidence/male-selector-windows-actions.json). |
| 2. Male/female selector | Implemented. Local browser fixture passed full-document switching, explicit unload, scoped low LOD and both rig-bound recording paths. **Hosted frozen acceptance passed** in the same corrected Windows run. |
| 3. More realism | Previous v3 shading retained. **No new authored/scanned textures, authored normal/roughness maps, eyebrow/lash geometry, short male hairstyle or skin scattering delivered in this follow-up.** These still need asset work, new render evidence and budget checks. |
| 4. Lip-sync | Existing tuning controls and phone crosscheck retained. No new independently reviewed reference or physical AV measurement; do not call the related PocketSphinx/Rhubarb acoustic families independent ground truth. Further tuning must follow actual evidence, not arbitrary extra jaw/tongue gain. |
| 5. i5-U / 16 GB | Benchmark now accepts either prepared studio. Actual laptop results and thermal/whole-system measurements remain user-side. No default quality increase based on cloud performance. |
| 6. Personal acceptance | **Hosted male paired install/update/uninstall passed**. Your actual PC install, saved-data recovery and unsigned-warning UX remain open. Signing optional; public redistribution remains uncleared. |

## Prepare and run the selector

From the developer checkout, after explicit normal speech/model setup:

```sh
.venv/bin/python tools/build_neural_studio.py --output artifacts/selector-female
.venv/bin/python tools/prepare_makehuman_male.py
.venv/bin/python tools/build_neural_studio.py --character artifacts/male-character --output artifacts/selector-male
.venv/bin/python tools/character_studio_server.py --female artifacts/selector-female --male artifacts/selector-male --sessions artifacts/selector-sessions --port 8082
```

The root opens the male studio. Choose the prepared character dropdown to switch.
No extra mesh thumbnails/preloads: **unload the old geometry/materials/textures,
lose its WebGL context, stop/release audio and prefetch, then navigate to a fresh
document**. Generation/export must finish or be explicitly cancelled before a
switch. Profiles/calibration remain keyed by model hash; recordings, cast tokens,
conversations and session lookups remain rig-isolated. Old recordings are never
silently rebound to a different model or viewer. Back up files and retain the old
build for old archives.

The server reads prepared static files only; it does not keep both decoded models
in RAM. Both characters share **one executor, lock and global busy slot** for CPU
speech. Each rig retains at most six ready ephemeral sessions in this run. As in
the single-rig server, old UUID session directories are cleared at startup after
binding succeeds; saved conversations are outside them and preserved.

**One loaded character per studio page, not a global browser/OS memory guarantee.**
Close other studio tabs/apps when benchmarking. Navigating back may restore an
unloaded document: reload it to restore its character. The paired path is WebGL
only; there is no unsupported native-male fallback. Opt-in loopback integration
uses character-scoped URLs and tokens; the root API alias targets male.

## Build your personal Windows app

After `windows/setup-neural.ps1`:

```powershell
.\windows\build-character-pair.ps1 -PersonalUseOnly
# Optional local frozen regression (requires development Node/browser tooling):
.\.venv\Scripts\python.exe tools/smoke_packaged.py --expected-model artifacts/male-character/character.glb
```

This runs explicit build-time downloads/preparation, creates a **male-default EXE
with both prepared characters**, and bundles their required notices. It needs no
Python/Node/GitHub account/model download at runtime. SciPy is build-time only and
excluded from frozen modules. The optional unsigned personal installer remains:

```powershell
.\windows\build-personal-installer.ps1 -PersonalUseOnly
```

The existing `build-portable.ps1 -IncludeNativeVulkan` remains the stock female
native-enabled build; it does not enable unsupported native male rendering.
The package collector now allowlists prepared static assets instead of collecting
arbitrary custom-studio contents. Session files, private notes and workspaces are
not taken from those directories. The integrity manifest is damage detection,
**not code signing or authenticity certification**. Never publish the built bundle.

## Repeatable laptop evidence — no remote substitutes

Close other studios. In the checkout, run one rig at a time, visibly, on your
usual power plan; record plugged-in/battery, Windows/browser/driver versions,
room temperature, speaker/headphone device and competing workloads:

```powershell
.\windows\benchmark.ps1 -Repeats 2 -Assets artifacts/neural-studio -Conditions 'My i5-U / 16 GB; plugged in; visible Chrome; add real conditions here'
# Keep a copy of artifacts/jali-benchmark-report.json before the next run.
.\windows\benchmark.ps1 -Repeats 2 -Assets artifacts/male-studio -Conditions 'Same PC and conditions; male'
```

This is a **developer server benchmark**, not frozen EXE cold-start timing. For the
actual EXE also record launch-to-ready and first-face times, whole process-tree
and Chrome/GPU memory, visible playback gaps and audio underruns. Worker peak RAM
is not whole-app RAM; render submissions are not displayed FPS. Record actual
start/peak CPU package temperature using a trusted sensor tool if available;
leave it **unavailable**, never inferred from Windows thermal-zone readings, if
there is no supported sensor. Short corpus runs do not certify sustained thermals.
Inspect reports/logs before sharing. Nothing uploads automatically. Use the low
preset if needed, but do not declare the final default tuned until results exist.

## Saved-data and physical acceptance on your PC

1. Stop the app. Copy the entire `%LOCALAPPDATA%\JaliVulkan` tree to a private backup
   outside the installation, and **export browser calibration/profile books**
   separately. Browser localStorage is not included in an AppData backup. Treat
   pairing keys, recordings and conversation text as private; do not upload them.
2. Keep the old complete executable folder and its manifest. Paired stores use
   `sessions\female`, `sessions\male` and their sibling `*-conversations`/`*-cast.json`
   files; legacy single-rig data is not silently moved or rebound. Keep desired WAVs
   before restart clears ephemeral UUIDs. Saved conversations contain their own media.
3. Install the personal build normally. Run `JaliStudio.exe --verify-installation`
   and `--doctor`. Generate/save a known public test dialogue, export a profile and
   verify both characters. Do not disable SmartScreen or download random DLLs.
4. Reinstall/update normally, verify the payload again, then load the saved dialogue
   and imported profile in its matching rig/build. Test no silent resynthesis.
5. Uninstall normally with the backup retained. Verify user data survived. Reinstall
   the matching build; if recovery is needed restore a **copy** into a fresh user-data
   location after stopping the app. Never overwrite the only good backup. Damaged or
   different-rig media must fail closed, not silently receive new bindings.
6. To measure **physical** AV offset, record actual speaker/headphone output plus the
   displayed face with a common clock/reference marker and report method, sign,
   uncertainty and repeated samples. Container timestamps or `audio.currentTime`
   alone cannot measure the laptop's speaker/display latency. Independently annotate
   acoustic/visual P/B/M closure, F/V contact, tongue and transitions on exact hashed
   WAVs before calling lip-sync tuning accepted. Full blink and three-quarter hair
   review remain separate checks.

## Executed local evidence and first Windows result

- **157 Python / 42 JavaScript tests pass**, plus both the explicit non-speech
  selector fixture and **NEW actual CPU speech for both selected rigs**. Local
  female uses `af_heart`, male `am_michael`; verified WAV/text/rig/provenance and
  unload markers are retained in [the local receipt](evidence/character-selector-local.json).
- The explicit-male developer benchmark completed **all three public cases** on
  this Linux software-browser sandbox. [Actual report](evidence/male-selector-linux-benchmark.json).
  This is not your i5, frozen startup, whole-system RAM or thermal acceptance.
- First dedicated Windows run
  [39023609869](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39023609869)
  **passed actual male frozen EXE / clean PATH / actual speech for both characters /
  switch-unload and male benchmark steps**, then failed in the installer step.
  [Exact steps and successful frozen notice](evidence/male-selector-first-windows.json).
  There was no wrapped-command error notice from the failed step; log retrieval's
  redirected host was unavailable. Do not claim an exact Chocolatey error text.
- The installer setup now guards an already-present compiler (like the passing
  stock workflow) and annotates any fresh Chocolatey error. The corrected workflow
  is being triggered by branch push because the integration denied manual dispatch
  with HTTP 403. **Corrected male hosted run 39024328601 passed.** **All 12 stock/native regression jobs also passed** for the same source `61e0315` in [39024328602](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39024328602). [Complete 12+1 acceptance receipt](evidence/character-selector-full-actions.json).

## Visual asset/scattering investigation (not delivered assets)

The current surface code preserves supplied normal/roughness maps via material
copy. It adds procedural skin detail only when the known skin material has no
normal map. A complete authored glTF PBR set should therefore supply its own
normal map and roughness map, correct tangent-space orientation/UV seams and
color spaces, and be reviewed under all three lighting presets. Existing
roughness controls still scale material response. This is an import path, **not**
evidence that new authored maps have been created.

For an i5-first scattering experiment, prefer an optional skin-only single-pass
wrapped-diffuse approximation before considering extra screen-space passes.
Three r174 physical transmission uses a transmission render pass/target; enabling
it is not free, and glass-like transmission is not skin subsurface transport.
Neither approach is currently enabled or measured here. A candidate needs a
thickness/masking strategy, oral/eye exclusion, energy/color safeguards, known
texture budgets, actual before/after frames and a measured low-preset regression
before adoption. No GPU cost or quality gain is being asserted from a design alone.

Brows/lashes and the male ponytail still use the source geometry. Material tint
cannot create missing strands or a distinct hairstyle. Next asset work must use
owned or explicitly licensed geometry/textures, preserve facial controls and
head attachment, and provide new camera/pose/groom evidence—not reuse these
selector screenshots as realism acceptance.

## Final hosted acceptance

**Source `61e0315641d0424f199e937b8c0dbc39f5114c40`: all 12 core jobs plus the
separate male Windows job succeeded.** This includes the existing stock female
native-enabled package/installer, new male-default paired WebGL EXE/installer,
actual CPU synthesis, both-character switch/unload, scoped low LOD, Windows
offline HTTP/file playback, sanitizers, Blender roundtrip and native Vulkan tests.
[Exact jobs/steps, notices, source lineage, scope and image hash](evidence/character-selector-full-actions.json).

The first male installer-step failure is retained. Its exact log text was not
retrievable; the correction guards the existing compiler and annotates fresh
setup failures. The corrected build/install tests actually ran and passed—none
were skipped. The first main run was superseded/cancelled, not counted as passing.
No binaries or weights were published. Neutral low-preset UI screenshot:

![Actual paired studio with male selected; not new realism approval](images/character-selector.png)
