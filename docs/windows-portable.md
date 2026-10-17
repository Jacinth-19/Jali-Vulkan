# Personal Windows portable build: WebGL and optional native Vulkan

## Male-default EXE with male/female selector — accepted 2026-10-17

Source **61e0315** passed **12 core + 1 dedicated male Windows job**:
[core](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39024328602) /
[male](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39024328601).
The male-default paired **WebGL** EXE was actually executed with Python/Node/gh
removed from its PATH; its requested male hash, new CPU speech for both rigs,
switch/unload, integrity/tamper and unsigned install/update/uninstall checks passed.
The stock female native-enabled package also passed in the same-source core run.
[Exact acceptance and preserved first installer failure](evidence/character-selector-full-actions.json).

Build with `windows/build-character-pair.ps1 -PersonalUseOnly` after explicit
normal setup. [Full commands, memory scope, profile/archive safety, benchmark and
actual-PC recovery checklist](character-selector-and-personal-acceptance.md).
One model per page and one shared inference slot; close other tabs for a bounded
browser total. No unsupported native-male fallback. Actual i5 thermals/physical AV,
your personal install/recovery and public redistribution remain unaccepted.
Signing stays optional. Earlier sections below describe historical checkpoints.


## Reviewed visual-fix batch v3 — 2026-10-17

Source **60cb4f1** passed **all 12 hosted jobs** in
[39021296279](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39021296279),
including actual Windows offline HTTP/file playback, **stock female frozen EXE
rebuild and execution without Python/Node/gh in PATH**, and unsigned personal
installer install/update/uninstall. [Exact steps, notices and original failed
cancellation-test run](evidence/makehuman-visual-fixes-actions.json).

The [mouth/lighting/brow-lash batch](makehuman-visual-fixes.md) is WebGL-only;
geometry and speech weights are unchanged. The male model/browser path passed,
but a custom male Windows EXE was not separately exercised. Existing user-PC EXEs
still need rebuilding; back up rig-bound profiles/archives and retain old builds
for old replay. The explicit developer two-fixture comparison is **not** automatic
archive migration. Personal signing stays optional; public redistribution,
human/physical-AV/target-i5 acceptance remain open. Earlier checkpoints below are
retained as history, not the current visual-fix acceptance.


## Male MakeHuman / skin update — 2026-10-17

Current WebGL skin/eye/hair runtime `d78fc3b` passed **all 12 hosted jobs** in
[39017428466](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39017428466).
The **stock female Windows EXE was actually rebuilt and run without Python, Node
or gh in its PATH**, followed by unsigned personal installer install/update/
uninstall tests. [Exact job steps and Windows receipts](evidence/makehuman-skin-actions.json).
Your existing PC EXEs still require a local rebuild; they do not auto-update.

The new **male MakeHuman gender-target variant** passed hosted asset and browser
validation; a male custom Windows EXE was **not separately exercised**. Use the
explicit [male preparation/custom package flow](makehuman-male-skin.md), not the
stock builder that resets the female asset. No live mesh selector is implied.
Keep provenance/licenses; back up rig-bound casts, conversations and archives,
and retain the previous build for verified old replay. Appearance/video stay
WebGL-only; human review, physical AV and measured i5-U/16 GB acceptance remain open.
Personal signing is optional. No public binary/weight release or redistribution
approval is implied by these tests.


This is an **unsigned personal build**, not a signed consumer installer and not
an approved redistributable release. Default builds use WebGL; an explicit
option includes the native Vulkan engine, shaders and loader (not a GPU driver). Build/test automation does not certify your laptop's speed,
Windows warning UX or physical audio/display synchronization.

## Build on your own Windows x64 machine

First complete [developer setup](windows-neural-studio.md). Then, from the checkout:

```powershell
.\windows\build-portable.ps1 -PersonalUseOnly
```

The explicit preparation step can download pinned assets/license notices; building
requires Python 3.11, Node, GitHub CLI and internet as documented in developer setup.
PyInstaller **6.16.0** collects only prepared studio assets, the pinned CPU speech
runtime, stock `af_heart` voice (plus explicitly installed optional stock voices)
and Windows analyzer—not your session store or home.
The generated receipt lists exact installed package versions and source commit.

Output: `artifacts/windows-portable/JaliStudio-Windows-x64.zip`. Extract the **whole
ZIP**, then double-click `JaliStudio.exe`. Choose renderer/preset in the launcher,
then Launch opens your browser on a free loopback port. Keep the launcher open;
Stop studio or closing it stops its owned server. The built app needs no
Python, Node, GitHub account, administrator install or runtime model downloads.
Windows may warn about the unsigned executable; do **not** disable security checks.
Use the developer launcher instead if you cannot establish trust in your own build.
For command-line serving without the GUI: `JaliStudio.exe --serve --port 0`.
See [new launcher, diagnostics and studio controls](four-upgrades.md).

Whole-utterance and bounded sentence-batched speech use CPU inference; presentation
is WebGL or the explicitly enabled optional native Vulkan backend.
The stock voice is not a clone or Arena `voice-00`. No microphone or cloud speech
service is used. Generation files remain under `%LOCALAPPDATA%\JaliVulkan\sessions`.
**UUID session directories are cleared on the next startup.** Save wanted WAVs and
manifests before restarting. Delete that local app-data directory to erase retained
recordings; deleting the extracted app removes its model/runtime files. Rebuild to
update; the portable ZIP itself has no background updater or auto-upload. An
[optional unsigned personal per-user installer](workspace-upgrades.md#6-personal-installer-and-release-boundaries)
now supports manual reinstall/update and data-preserving uninstall. Saved dialogue
WAV archives live separately from ephemeral sessions and survive startup cleanup.

## Redistribution is deliberately blocked as a release claim

`phonemizer-fork 3.3.2` carries GPL-3.0. `espeakng-loader 0.2.4` bundles eSpeak but
its wheel lacks complete licensing metadata/notices. Copying package metadata is
**not** a complete corresponding-source/compliance solution. The combined bundle's
redistribution obligations have not been established, and this work does not
relicense the repository. `PERSONAL-BUILD-ONLY.txt` travels with your local build.
Do not publish the ZIP/executable until permissions, notices and source obligations
have been separately reviewed. Noncommercial intent is not a license exemption.

Hosted Windows CI builds with `--personal-build --no-archive`, exercises the
**frozen executable** from an unrelated working directory with Python/Node/gh
removed from its PATH, and generates whole and batched performances in Chrome.
It uploads **proof JSON/logs only**, never the executable, neural weights or bundle.
This is a hosted execution check—not an independently clean OS image, a physical
laptop benchmark, an installer-security audit or human acceptance.

## Executed evidence

Current eye/hair runtime source **8af0695** passed **all 12 jobs** in
[39003511599](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/39003511599),
including a fresh frozen Windows EXE build/execution and unsigned installer
install/update/uninstall. [Exact evidence and prior fixture failure](evidence/eye-hair-actions.json).
Existing EXEs do not update in place. Back up rig-bound archives/profiles before
rebuilding; see [appearance/character scope and compatibility](eyes-hair-characters.md).

Previous workspace checkpoint: [run 38960192424](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38960192424)
passed all **12 jobs** for source `1b527c0`, including frozen native/WebGL execution
and unsigned per-user installation, clean application-data doctor, reinstall/update
with retired-file cleanup, payload re-verification and data-preserving uninstall.
[Exact current evidence and earlier failures](evidence/workspace-upgrades-actions.json).

Historical native/integrity foundation:

[Run 38913502148](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38913502148)
passed all **11 jobs** for source `caa1e95`: native Windows source execution,
optional frozen native/WebGL package, real CPU speech/batches, integrity failure
and recovery tests, runtime readback and untouched-installation checks. Only
public proof/logs are published, not the personal app or speech weights.
[Exact jobs/artifact digests and failed attempts](evidence/windows-native-integrity-actions.json).

Historical CPU/WebGL foundation:

[Actions run 38905755693](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38905755693)
passed all ten jobs for source `3202be0`, including **Build personal-only frozen
CPU/WebGL app** and **Run the frozen app with Python, Node and gh removed from its
PATH**. Both a fresh whole-utterance recording and a two-chunk completed recording
passed actual Chrome/WAV/rig checks. The earlier run 38903183684 also passed all ten.
See [job-by-job evidence and the separate offline-checkpoint reliability note](evidence/rich-stream-portable-actions.json).
No executable/ZIP is published by these runs; build your personal copy locally.

## Offline installation checks

Personal builds now generate `installation-manifest.json` covering every bundled
regular file, including the EXE, libraries, model, rig and notices. Startup checks
sizes and SHA-256 hashes before importing the studio; missing, changed or extra
files fail closed. Filesystem links/reparse points and case-colliding names are
rejected. Keep recordings, notes and diagnostics **outside** the installation.

```powershell
.\JaliStudio.exe --verify-installation
.\JaliStudio.exe --verify-installation --diagnostics-file "$env:TEMP\Jali-install-check.json"
```

This read-only mode does not start a server, run synthesis, or clear sessions.
Exit 0 means files match; exit 2 means an integrity/access error. Repair by
extracting your entire original personal-build ZIP into a **new empty folder**,
or rebuilding from your trusted checkout. Do not mix versions, disable security,
or download random replacement DLLs. A ZIP build also writes a `.zip.sha256`
sidecar. Neither that checksum nor the **unsigned** manifest proves authenticity
against an attacker who replaces both files. This is **not code signing or a
redistribution license clearance**.

After a successful preflight, ordinary server startup failures emit actionable
JSON and save `%LOCALAPPDATA%\JaliVulkan\last-startup-error.json` (or your chosen
external `--diagnostics-file`). An occupied port can be avoided with `--port 0`.
Bootloader/Windows errors occurring before Python starts cannot be caught by
this code: keep the console error and rebuild from the trusted source instead.
Hosted tests now explicitly exercise intact, tampered, missing-analyzer and
restored installations, plus normal startup refusing a corrupted package.
These checks passed on actual frozen Windows in run 38913502148, including a
post-runtime verification that the installation was not modified.

## Optional personal native-Vulkan bundle

The default remains CPU speech + WebGL. To also include the native renderer:

```powershell
.\windows\setup-native.ps1
.\windows\build-portable.ps1 -PersonalUseOnly -IncludeNativeVulkan
```

The explicit option adds the built native EXE, Vulkan loader, decoded human rig,
four shaders and upstream notices. **No GPU driver or Chrome DLL is bundled.**
`Native-Studio.cmd` (or `JaliStudio.exe --native`) enables it; choose Native Vulkan
in the page. Ordinary EXE launch still offers WebGL without Vulkan. Shader paths
are resolved inside the extracted package, not against the build machine's
checkout. Native engine logs live under LOCALAPPDATA, outside the verified
installation. The same personal-use/unsigned/redistribution restrictions apply.
The optional frozen-native path passed hosted Windows in run 38913502148 with
Python/Node/gh removed from its runtime PATH. The browser generated actual new
CPU speech and two sentence chunks with native readback; this is separate from
the earlier CPU/WebGL-only proof.

GitHub-hosted Windows runs elevated, so the secure Vulkan loader intentionally
ignores `VK_ICD_FILENAMES`. Software CI explicitly registers **only its own**
temporary ICD manifest on that disposable machine and removes that value in an
`always()` cleanup step. This is guarded against local/self-hosted use; the
normal user setup never changes the driver registry or disables loader security.

## New launcher verification

The upgraded chooser's actual frozen **Launch/Stop**, stripped-PATH execution,
Tk/Tcl collection, offline integrity checks and real native device-readback doctor
passed hosted Windows in [run 38935343354](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38935343354).
The same run passed all eleven jobs, including detailed native 256/512/768 images.
[Exact evidence and remaining gates](evidence/four-upgrades-actions.json).
This does not replace physical laptop, perceptual, legal or signing acceptance.

See the dated [engineering licensing review](licensing-review.md) for additional
notice/provenance/owner-license blockers. Signing is optional for your personal
version; no public redistribution clearance is claimed.
