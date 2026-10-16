# Offline articulation review / early laptop checkpoint

**2026-10-16 — browser slice delivered; M3/M7 remain partial.**

Download/extract `Jali-Laptop-Playback-Checkpoint.zip`, then open `index.html`
in current Edge or Chrome. No Python, Node, neural weights or speech API key is
needed **for playback**. The live **Laptop playback checkpoint** preview offers
the same UI. Full [Windows instructions](windows-playback-checkpoint.txt) are
also included in the pack as `README.txt`.

## What is new

- Three fixed public Kokoro stock `af_heart` recordings, requested text,
  exact-WAV/dialog estimated cues and the detailed CC0 head.
- Audio-clock animation, per-cue seeking, half-speed inspection and orbit/zoom.
- Per-recording pending/acceptable/problem declarations and notes; switching
  recordings retains notes in memory. No automatic quality score.
- Explicit JSON download of notes, conditions, audio/rig identity and playback
  observations. No automatic saving or uploading. Inspect before sharing:
  exports contain user-entered notes and browser/GPU/CPU/memory hints.
- Bounded 90-second measurement at normal speed, neutral styling and zero trim,
  with procedural motion disabled. Actual audio completion ends the run;
  cancellation, pause, seeking, settings changes, resize, hidden tabs or context
  loss interrupt/invalidate it. Empty/one-frame samples have no FPS result.
- Observed render-call cadence/frame gaps and CPU-side pose/draw submission time.
  These **are not presented/display FPS, GPU timer queries, physical AV latency,
  system RAM inventory or target-laptop performance guarantees**. The animation
  loop targets at most 30 fps; do not substitute that target for the observed rate.
- Package admission validates public text, WAV hash, cue/dialog/manifest binding,
  CPU stock-voice provenance and model/viewer identity. ZIP entries are explicitly
  allowlisted so leftover notes or files cannot be swept into a rebuild.

## Validation actually executed

[Actions run 38841826083](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38841826083)
passed **all eight jobs**, source `a8b7175938b192e62add21053094dc6565d0f208`:

- Native matrix, sanitizers and existing native software-Vulkan/browser checks.
- Fresh Linux CPU Kokoro synthesis, analysis of each exact WAV/dialog and actual
  detailed-head browser integration; 74 Python and 12 JavaScript tests.
- Linux checkpoint builder plus real HTTP and file-URL browser playback tests.
- A separate **Windows hosted runner with installed Chrome**, testing the same
  CI-built pack over HTTP and file URLs; JavaScript contracts also run on Windows.

The browser checks verify all three embedded WAV hashes/playback/face identities,
note retention, actual audio-end completion, invalid cancellation/speed-change
samples, downloaded JSON contents, pending review states and mobile overflow.
Web security is not disabled. Both local test modes observed no external HTTP
requests or browser errors. The Windows job uses permitted software fallback in
CI; its success is not proof of physical GPU acceleration or laptop performance.
The Linux neural-plus-checkpoint job took **3m43s**; Windows browser job **3m0s**.

The **local ZIP** is 8,291,251 bytes / 15 allowlisted entries, with ZIP CRC and all
14 payload hashes verified. Its separate local HTTP/file evidence and archive
SHA-256 are in [`evidence/playback-checkpoint-local.json`](evidence/playback-checkpoint-local.json).
The Windows job tested an independently generated **CI-built** pack from the same
source, not a claim of byte-identity with this local archive (session IDs differ).
[Hosted metadata](evidence/playback-checkpoint-actions.json) preserves job results
and three-day artifact links: `laptop-playback-checkpoint` contains its ZIP;
`windows-browser-playback-evidence` contains actual Windows browser reports.

## Developer reproduction

After studio setup, with no interactive server on port 8082:

```sh
.venv/bin/python tools/run_neural_ci.py
.venv/bin/python tools/build_playback_checkpoint.py
node tools/smoke_playback_checkpoint.cjs
```

`run_neural_ci.py` creates fresh public speech and review files; startup clears
prior studio sessions. Preserve any wanted private recordings elsewhere first.
The pack builder only consumes the fixed public corpus and does not include
neural weights, executables or private recordings. The browser smoke test defaults
to the pinned Linux software Chromium; set `JALI_BROWSER_CHANNEL=chrome` only
where a compatible installed Chrome exists, as in the Windows job.

## What we need from the target laptop

1. Extract/open the pack, listen to each recording, inspect at normal/half speed.
2. Note sound/time/visible problems (P/B/M seal, F/V contact, L tongue, vowels).
   Midpoint PNG inspection alone did not establish geometric contact or alignment;
   strengths have not been blindly retuned or declared accurate.
3. Measure representative recordings a few times with the tab visible; note
   Windows version, power mode, plugged-in state and other running applications.
4. Save the JSON, inspect it, and share it if comfortable. Notes are lost on reload
   unless exported. User ratings are declarations, not independently verified QA.

**Still open:** local Windows speech/analyzer setup and performance, long-run/
thermal tests, full-utterance perceptual review, independently aligned phonemes,
physical speaker/display timing, and the rich native Vulkan renderer. This pack
makes user-device observations possible; it does not close those gates by itself.

## Subsequent Windows backend milestone

The playback ZIP itself is still face/audio playback only. The separate Windows
x64 developer backend has since passed actual new CPU speech, Windows analysis
and live Chrome integration: see [Windows neural studio](windows-neural-studio.md).
The earlier eight-job result above remains historical evidence for this pack; the
new nine-job result does not establish target-laptop performance or an installer.
