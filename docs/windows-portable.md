# Personal Windows portable CPU/WebGL build

This is an **unsigned personal build**, not a signed consumer installer and not
an approved redistributable release. The separate native Vulkan developer engine
is **not** included. Build/test automation does not certify your laptop's speed,
Windows warning UX or physical audio/display synchronization.

## Build on your own Windows x64 machine

First complete [developer setup](windows-neural-studio.md). Then, from the checkout:

```powershell
.\windows\build-portable.ps1 -PersonalUseOnly
```

The explicit preparation step can download pinned assets/license notices; building
requires Python 3.11, Node, GitHub CLI and internet as documented in developer setup.
PyInstaller **6.16.0** collects only prepared studio assets, the pinned CPU speech
runtime, stock `af_heart` voice and Windows analyzer—not your session store or home.
The generated receipt lists exact installed package versions and source commit.

Output: `artifacts/windows-portable/JaliStudio-Windows-x64.zip`. Extract the **whole
ZIP**, then double-click `JaliStudio.exe`. Keep its console open. It opens your
normal browser at `http://127.0.0.1:8082`; Ctrl+C stops it. The built app needs no
Python, Node, GitHub account, administrator install or runtime model downloads.
Windows may warn about the unsigned executable; do **not** disable security checks.
Use the developer launcher instead if you cannot establish trust in your own build.
Port 8082 already occupied? Run `JaliStudio.exe --port 8083`.

Whole-utterance and bounded sentence-batched speech use CPU inference and WebGL.
The stock voice is not a clone or Arena `voice-00`. No microphone or cloud speech
service is used. Generation files remain under `%LOCALAPPDATA%\JaliVulkan\sessions`.
**UUID session directories are cleared on the next startup.** Save wanted WAVs and
manifests before restarting. Delete that local app-data directory to erase retained
recordings; deleting the extracted app removes its model/runtime files. Rebuild to
update; this prototype has no background updater, registry installer or auto-upload.

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
These new tests are not claimed passed until the new Actions run finishes.

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
The new optional frozen-native path is pending hosted Windows verification;
the prior CPU/WebGL package proof must not be counted as evidence for it.

GitHub-hosted Windows runs elevated, so the secure Vulkan loader intentionally
ignores `VK_ICD_FILENAMES`. Software CI explicitly registers **only its own**
temporary ICD manifest on that disposable machine and removes that value in an
`always()` cleanup step. This is guarded against local/self-hosted use; the
normal user setup never changes the driver registry or disables loader security.
