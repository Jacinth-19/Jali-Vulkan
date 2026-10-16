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
