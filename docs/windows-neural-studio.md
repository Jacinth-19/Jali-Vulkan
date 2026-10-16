# Windows x64: new text → local neural speech → live face

**Status, 2026-10-16:** the developer backend has passed actual Windows hosted
CPU inference, Windows Rhubarb analysis and live Chrome/WebGL form-to-face tests.
This is no longer playback-only or a Linux-only analyzer. **Your i5 laptop has
not been tested.** There is no standalone installer or rich native Vulkan port.

## Prerequisites and first setup

Use the current session branch `arena/3284941c-jali-vulkan`, not the old main
snapshot. From a PowerShell terminal in this repository:

- Windows x64, **Python 3.11 x64** with the `py` launcher.
- **Node 22/npm**, and **GitHub CLI (`gh`)** for explicit public character/license
  downloads. Authenticate using `gh auth login` if needed; use its normal browser
  flow. Never paste credentials into chat. No paid speech API/key is needed.
- Internet during setup, several hundred MB of downloads and sufficient free disk
  for Python/Node dependencies, models and caches. Allow several GB rather than
  assuming the former small playback ZIP is a complete backend installation.

```powershell
.\windows\setup-neural.ps1
```

The script makes `.venv`, installs pinned Python and Node dependencies (npm hooks
are disabled), explicitly prepares the stock voice/model, the pinned official
Windows analyzer, and the licensed optimized character/viewer. Each native step
is checked for failure. This is developer setup, not a machine-wide installer.
Respect local/organizational script policy: do not disable security policies to
run it. Equivalent approved commands are:

```powershell
$env:PYTHONUTF8 = '1'
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r tools/requirements-neural-studio.txt
npm.cmd ci --prefix tools --ignore-scripts
.venv\Scripts\python.exe tools/prepare_kokoro_cpu.py
.venv\Scripts\python.exe tools/build_neural_studio.py
```

Stop if a command fails. A fresh consumer Windows installation may need runtime
prerequisites not exercised by a developer-oriented GitHub image; do not download
random DLLs. Report the exact dependency error before changing the installation.
The interactive PowerShell launchers are provided as developer conveniences;
CI exercised the corresponding Python/Node setup and server pipeline, not a
clean consumer installer or the `py`-launcher installation experience.

## Start and use

```powershell
.\windows\start-neural.ps1
```

After the server-start message, open **http://localhost:8082** in Edge or Chrome.
Enter a new bounded English script and choose **Generate & play**. This actually
runs local Kokoro q8 CPU inference, analyzes that new WAV with its requested
script, and plays the detailed WebGL face using matching hash-bound cues.

- Runtime requests do not download models, call a hosted speech API or fall back
  to eSpeak audio. eSpeak NG is only the packaged text phonemizer.
- The launcher binds to **127.0.0.1**, not the LAN. Do not expose this development
  server publicly; CSRF checks are not remote authentication.
- Keep **one studio instance** running. Startup deletes prior UUID session
  directories; download wanted WAVs/manifests first. Do not launch another
  instance against the same session store, even on a different port.
- Ctrl+C stops serving. There is no immediate generation-cancel UI; an active
  worker can take time to finish within its per-stage 90-second bounds.
- Setup is networked; generation/playback works locally after successful setup.
- Remove the repository to remove this project-local environment/models/cache
  and recordings; pip/npm global download caches are managed separately. Download
  any wanted outputs first. Do not delete unrelated system Python/Node installs.

For a model-free face-only check, use the separate
[offline playback pack](playback-checkpoint.md). It does **not** generate speech.

## What Windows execution actually proved

[Actions run 38843451199](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38843451199),
source `aacafc4f69b3f45aab3b1e45e53af6478d73a977`, passed **all nine jobs**.
The new **Windows local neural speech, analyzer and live face** job took **2m21s**,
including setup and integration testing. It did not reuse Linux speech recordings.

| Public corpus case | Actual audio | Synthesis | Exact-WAV analysis | Total pipeline | Worker peak working set |
|---|---:|---:|---:|---:|---:|
| Closures | 3.456 s | 0.8623 s | 2.3613 s | 5.3027 s | 291.49 MiB |
| Contacts | 4.075 s | 0.9612 s | 2.2534 s | 4.9939 s | 296.72 MiB |
| Vowels | 3.605 s | 0.8765 s | 2.7616 s | 5.2443 s | 291.01 MiB |

These are **three individual Windows runner samples**, not repeated p95 results,
physical playback latency, total app RAM or laptop predictions. Total includes
process/import/model-load overhead, so it exceeds synthesis + analysis. Peak
working set uses Windows `GetProcessMemoryInfo` for the speech subprocess,
including dependencies/model, not whole-system memory or browser GPU memory.
Actual Windows OS/CPU inventory is retained in the hosted artifact.

The Windows job checked CPUExecutionProvider only, reviewed model/voice hashes,
the actual Windows executable hash and exact-WAV/audio association. Real Chrome
submitted all three texts, played/paused/sought, checked mouth morphs, sync-off
reset, natural-end rest, history, mobile layout and absence of external browser
requests/errors. It produced 22 neutral review frames across all nine estimated
classes and an offline MP4 using that Windows-generated speech. This establishes
functional execution, **not naturalness or phoneme accuracy**.

Linux regression also passed three new actual recordings. The full model-free
Linux suite passed **79 Python + 12 JavaScript tests**; the Windows job ran the
cross-platform neural subset and JavaScript contracts, not all native Linux tests.
The separate Windows HTTP/file playback job also remained green.

## Analyzer provenance and platform behavior

- Windows x64 selects official Rhubarb 1.13.0 **Windows.zip**, not the Linux npm
  executable. Cache paths and executable pins differ by platform. No arbitrary
  binary URL, DLL, command or alternate-platform fallback is accepted.
- Official release archive: **88,700,994 bytes**, SHA-256
  `189ac55dae253dba3994d4075b8375b615f255759c105c7ed21bd88ad7728386`.
- `rhubarb.exe`: **2,701,312 bytes**, SHA-256
  `d31a3030bcb11c39c175cdba45f8152456d7d2a288a8198b820f3b8c4f37ab2b`.
- [Inventory run 38843072059](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38843072059)
  downloaded the official release and hashed archive/executable bytes **without
  executing** them before these pins were added. This is byte provenance, not an
  independent audit of the executable or a separately published upstream digest.
- Setup checks the whole archive, only extracts allowed executable/resource/notice
  paths, rejects traversal/links, and repairs cached files from verified bytes.
  Startup and analysis recheck the selected executable. Resources are checked
  during setup, not independently rehashed from the archive on every request.
- Linux retains its original checksum-pinned npm archive/binary. Unsupported
  OS/architecture combinations fail explicitly. macOS/ARM64 are not ported.
- Windows CI cleanup kills only its spawned server process tree, not arbitrary
  Python/Chrome instances. The browser uses the selected Python interpreter for
  FFmpeg export, not a hard-coded Unix `.venv/bin/python`.

Machine-readable [Windows metrics and Actions/audit evidence](evidence/windows-neural-actions.json)
retain the observed values and three-day artifact links. Only the fixed public
synthetic corpus is uploaded, never neural weights, arbitrary sessions or tokens.
The hosted artifacts were not independently downloaded here; GitHub API job
conclusions and the emitted public metric annotation were verified directly.

## Remaining acceptance gates

Run on the actual Windows/16 GB/i5 laptop before choosing performance settings:
check intelligibility/pronunciation and full-utterance motion; measure cold and
repeat runs, memory, render cadence, power/thermal behavior and longer scripts.
Unknown clean-machine prerequisites, non-ASCII installation paths, sustained
playback and interrupted-process recovery still need coverage. Physical AV
latency, independently verified phoneme alignment, incremental speech and the
richer Vulkan renderer remain separate unfinished workstreams. Stock `af_heart`
is not the earlier external voice-00 and is not a cloned identity.

## Subsequent one-command benchmark

After setup, run `windows/benchmark.ps1` to collect repeated fresh speech and
browser observations in an isolated run. [Benchmark instructions](windows-benchmark.md)
explain the one-file report, exact-WAV independent references and M4 compatibility
audit. The actual PowerShell benchmark entry point passed in later nine-job run
38844926069; this does not change the distinction between hosted and laptop data.
