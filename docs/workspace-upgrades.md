# Character/workspace upgrades — supported contracts and remaining gates

Implementation adds mapped GLB importing, an offline-prepared WebGL LOD, bounded
multi-speaker dialogue with durable local WAVs, an opt-in loopback command/event
API and a personal per-user installer. This is **not universal character support,
simultaneous multi-avatar rendering, a public API or a legally cleared release**.

Validation: **142 Python / 33 JavaScript tests** and **all 12 hosted jobs passed**
in [38960192424](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38960192424),
source `1b527c0`. This includes actual Blender round trips, custom-runtime
rendering, genuine alternate-voice dialogue, Linux/Windows speech/WebGL/Vulkan,
frozen runtime and unsigned installer install/update/uninstall. Local genuine
256 / 15 FPS export decoded all 79 frames.
[Exact evidence, scope and earlier failed attempts](evidence/workspace-upgrades-actions.json).

## Updating a source Windows installation

```powershell
npm.cmd ci --prefix tools --ignore-scripts
# Optional, explicit stock voice downloads from the pinned, verified archive:
.\.venv\Scripts\python.exe tools\studio_voices.py --install af_bella
.\.venv\Scripts\python.exe tools\studio_voices.py --install am_michael
.\.venv\Scripts\python.exe tools\build_neural_studio.py
.\windows\launch-studio.cmd
```

Restart the server after installing voices. `af_heart` remains the default.
The two optional voices are stock Kokoro identities, **not voice-00 or clones**.
Every job pins/rechecks the selected voice tensor and records voice SHA/speed;
the actual resulting WAV is analyzed with that turn's text, as before. No runtime
model or voice downloads are added.

## 1. Importing a character and reusing its mapping

Only self-contained **GLB 2.0** is accepted (32 MiB incoming, decoded accessor
budget 512 MiB; 100,000 vertices / 160,000 triangles / 128 skin joints; 16 PNG/JPEG
textures up to 4096 per side, 128 MiB combined uncompressed RGBA).
Decoded buffer views are capped at 512 MiB too; imported cameras/lights are rejected. External URIs, unsupported required extensions,
ambiguous mappings, nonfinite geometry and out-of-budget data are rejected.
The resulting canonical package is separately hash-bound and validated.

```powershell
node tools/character_cli.mjs inspect --input my-face.glb --output inspection.json
```

Copy `inspection.json`'s **template** object into `my-map.json`, filling its bone
and morph names and actual asset license/source. These are reusable data files,
not edits to application source. All 11 speech channels plus two blink channels
are required; additional supported expression channels may be mapped too. A
missing optional expression morph cannot magically produce that expression.

```powershell
node tools/character_cli.mjs import --input my-face.glb --profile my-map.json --output artifacts/my-character
.\.venv\Scripts\python.exe tools\build_neural_studio.py --character artifacts/my-character --output artifacts/my-character-studio
.\.venv\Scripts\python.exe tools\neural_studio_server.py --assets artifacts/my-character-studio --bind 127.0.0.1
```

Profile schema: `jali-retarget-v1`; `bones` maps canonical Head/LeftEye/RightEye to
unique source nodes; `morphs` maps canonical channels to source target names.
`space` is `jali-y-up-world-axes-v1`: model in metres, Y-up and face toward +Z.
Eyes must be direct children of Head in one skin; Head ancestors need positive,
uniform scale. Imported head motion uses world-aligned yaw-Y/roll-Z; gaze is
converted into the rest Head-parent frame, preserving bone rest orientations.
Portrait sizing, contacts, expression coverage and artistic quality still need
review. This is not auto-rigging, FBX importing or automatic axis/anatomy discovery.

`character.json` records source/model/profile SHA-256 and declared provenance.
Imported assets are **not assumed CC0**. Custom rigs are WebGL-only until their
native representation/parity is explicitly ported. Separate prepared studios can
use different meshes; the cast editor below shares the currently prepared mesh.

The hosted Blender test uses factory-startup Blender to actually import/export a
synthetic **3-joint / 13-morph alias-mapped rig**, then compares 16 skinned,
morphed world-space poses bidirectionally (including all 13 required morphs), plus
triangle counts. Its scope is that
fixture and recorded Blender version, not arbitrary production avatars or DCCs.

## 2. LOD and resource management

Preparation builds `model/low.glb` using Meshoptimizer simplification and 512-pixel
texture resampling. Skin/morph vertex correspondence is retained by the transform.
The default prepared head changes from **53,116 vertices / 83,686 triangles** to
**33,520 / 37,842**; its compressed low GLB is **3,398,424 bytes** in the local build.
LOD is approximate: lip seal, teeth contacts and rendering quality are not approved
by vertex counts. Native keeps its separately prepared full-detail asset.

Choose Low LOD in **Resources & local integration**, or use `?lod=low`. The page
reloads so only one mesh variant is resident; dialogue drafts persist. The loader
checks the LOD hash and source rig. Exports distinguish source speech rig from
actual `render_asset` identity. Natural idle defaults to a 2 FPS cap; selected
paused speech is static. Hidden-page RAF rendering is suppressed. Active speech
keeps the selected performance cap. These are caps, not target-i5 measurements.

**Unload character and audio** explicitly interrupts playback, revokes viewer
WAV URLs, removes mesh references and disposes geometry/materials/textures,
postprocessing, controls and the WebGL context. It also closes the optional native
worker, releasing its Vulkan allocation; a busy frame can require retrying Unload. Reload restores the scene. Server
sessions/saved WAVs remain on disk; this is not deletion of user data. CPU speech
workers already exit after each job, releasing their model runtime. No second
neural model is loaded for a second voice.

## 3. Dialogue, durable audio and sentence navigation

Under **Dialogue & cast**, select a speaker, queue paragraphs, then add another
speaker's paragraphs if desired. Play, Pause, Resume, Previous/Next and Interrupt
control a single shared audio player. Navigation interrupts owned generation before
moving; it does not auto-play the new sentence. Each turn uses a newly verified
WAV/text pair or an explicitly restored saved pair. No internally incremental
Kokoro, gapless playback or paragraph-wide prosody is claimed.

Bounds: **128 turns, 20,000 text characters total, 160 per turn**, one active
inference job/two CPU threads, one active speaker/mesh, six ephemeral completed
sessions, five saved conversations at **50 MiB each**. Completed turn audio/cues
are pinned before six-session eviction. Pin/save failure stops the queue rather
than pretending it was saved. The selected turn remains after interruption.
A paused generation may finish and save, but the next sentence waits.

Save/load/delete work through the local server's conversation store, a sibling of
the session folder (`sessions-conversations` in a normal portable user-data root).
That store survives server restarts and session cleanup. Saved WAV replay checks
waveform/text/cues/rig; missing or mismatched archived media does **not silently
regenerate**. A script/profile JSON export (256 KiB maximum) contains **no audio**; importing it
creates new turn identities for explicit regeneration. Changing an already saved
speaker identity requires a new character ID/conversation. Importing a script into
a different rig regenerates speech/cues instead of reusing another rig's archive.

## 4. Multiple characters, voices and budgets

The active cast is saved atomically beside the session folder (`sessions-cast.json`
in portable user data), bound to its rig, so it survives launcher restarts/free-port
changes. A damaged, different-rig or unavailable-voice cast file is kept with an
explicit warning, not silently overwritten on page load. Restore the voice/rig
or back up the file before explicitly saving a replacement.

Up to eight cast profiles have separate ID/name, installed stock voice, speed and
captured calibration/manual performance/appearance. Save a character with the
current facial controls, select it and queue its turns. Voice/speaker snapshots
are validated per job (not looked up again midway through inference). Archive
metadata pins the exact speaker profile. Different personas use **one currently
prepared mesh**, sequentially. Different prepared-character studios are supported,
not concurrent distinct meshes, scenes, simultaneous speaking or eight runtimes.
Limits are per studio process, not a system-wide governor; do not launch several
studios in parallel on the target i5. Custom asset directories get separate default
session stores; an explicit `--sessions` path must not be shared by live instances.

Browser drafts/profile snapshots are local to browser origin and rig SHA; use
script export/import to move them. Saved audio is server-side. Clearing browser
storage does not erase the server archive. Uninstall preserves user data.

## 5. Local application API (explicit opt-in)

Start the source server bound to loopback with a private pairing key file:

```powershell
.\.venv\Scripts\python.exe tools\neural_studio_server.py --bind 127.0.0.1 --integration-key-file "$env:LOCALAPPDATA\JaliVulkan\integration.key"
```

In the personal frozen app, check **Enable local-application control** in the
launcher (off by default), or run:

```powershell
.\JaliStudio.exe --serve --integration-key-file "$env:LOCALAPPDATA\JaliVulkan\integration.key"
```

The file is created if absent, never printed or served in `/api/config`. Protect
its folder with your user's Windows ACLs; POSIX creation uses mode 0600. To rotate,
stop the server, remove the key file and restart. Never commit/share it. Open the
studio and check **Allow paired local app playback control**. No browser means
no playback consumer. The normal UI token is a CSRF token, not public-service
authentication; neither this nor the existing server should be exposed publicly.

The examples below use the source server's default port 8082. The GUI launcher
chooses a free port: pass `--url` with the actual loopback URL displayed by the
launcher when using this client with the GUI.

Example standard-library client (reads the key file, not the command line):

```powershell
.\.venv\Scripts\python.exe tools\integration_client.py --key-file "$env:LOCALAPPDATA\JaliVulkan\integration.key" submit --speaker default --text "Please bring the blue bag."
.\.venv\Scripts\python.exe tools\integration_client.py --key-file "$env:LOCALAPPDATA\JaliVulkan\integration.key" expression --style warm --intensity .4
.\.venv\Scripts\python.exe tools\integration_client.py --key-file "$env:LOCALAPPDATA\JaliVulkan\integration.key" events --after 0
```

- `POST /api/integration/commands`, bearer key: strict JSON command types `submit`
  (text/speaker), `pause`, `resume`, `interrupt`, `expression` (expression/intensity).
- `GET /api/integration/cast`, bearer key: current IDs/voices and shared limits.
- `GET /api/integration/events?after=N`, bearer key: cursor, `gap`, event journal.
  Events include accepted/delivered/expired, command-done/error, playback
  loaded/play/pause/ended/error, turn-start/done and interrupted.
- Non-loopback clients and browser `Origin` requests to these external endpoints
  are rejected. No CORS wildcard. No URLs, arbitrary files, model downloads or
  shell commands are accepted. Integration is unavailable unless enabled at start.
- Queue 32 commands / 60-second TTL, one browser consumer with a 10-second lease,
  256 events with explicit journal gaps. Delivery is **at most once**, not exactly
  once: a browser crash can leave delivered work without completion. Do not
  auto-retry a submit without checking events. Restart resets the event cursor.
- An idle `submit` appends and starts at the newly submitted turn; a running queue
  appends it behind current work. Manual expressions remain authored, not inferred.

## 6. Personal installer and release boundaries

First rebuild your personal portable bundle, then use free Inno Setup 6.3+:

```powershell
.\windows\build-portable.ps1 -PersonalUseOnly -IncludeNativeVulkan
.\windows\build-personal-installer.ps1 -PersonalUseOnly
```

The wrapper above deliberately rebuilds the **stock head**. For a previously
imported custom character, instead install the pinned packager, explicitly prepare
that character into the default packaging directory and package it directly:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0
.\.venv\Scripts\python.exe tools\build_neural_studio.py --character artifacts/my-character
.\.venv\Scripts\python.exe tools\package_windows.py --personal-build
.\windows\build-personal-installer.ps1 -PersonalUseOnly
```

Do not include native Vulkan for a custom import without an explicit native port.
The **unsigned** installer uses per-user installation,
no admin requirement, Start-menu launcher/uninstaller, app-process closure during
updates and same-AppId reinstall/update support. Dependency/asset diagnostics
remain in the launcher/`--doctor`; verification is fail-closed. Updates are manual
installers, not a network updater. Each update replaces only the application-owned
`application` payload subfolder. Keep recordings/notes outside the install
directory. Inno uninstaller files are outside the strictly inventoried payload. Uninstall removes the application but **preserves
JaliVulkan user data**, including saved conversations. Delete that data manually
only after backing it up. Signing is optional and does not block personal use.

Hosted tests install into a path with spaces using isolated `LOCALAPPDATA`, run
integrity/dependency checks, reinstall and uninstall, and verify a user-data
sentinel survives. This is a clean application-data profile on a hosted Windows
image, **not every Windows version or a fresh physical PC**. The installer and
bundle are never uploaded as CI artifacts.

[Engineering licensing review](licensing-review.md), [release gates](release-gates.json) and `tools/release_inventory.py --output ...`
record an engineering license/notice inventory. **Public redistribution is still
not approved**: GPL phonemizer/eSpeak corresponding-source/combined-work duties,
upstream q8 provenance and all user-imported licenses require resolution. An
unsigned personal installer is not a completed licensing clearance or legal
opinion. No public executable/weights release is made by this work.
