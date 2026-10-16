# Four studio upgrades

Implemented 2026-10-16. Local verification: **130 Python tests, 22 JavaScript
tests**, and an actual Chromium/WebGL control/transport test using the real head
and explicitly synthetic **non-speech** PCM/cue fixtures. Current hosted Windows,
frozen-launcher and native-resolution acceptance is pending the new Actions run;
the older all-green run is not evidence for these changes.

## Performance presets and device observation

| Starting preset | Long-edge/frame limit | FPS cap | WebGL pixel-ratio cap |
|---|---:|---:|---:|
| Low | 256 | 15 | 0.75 |
| Balanced | 512 | 30 | 1 |
| High | 768 | 60 | 1.5 |

Resolution/FPS are also separately adjustable; settings persist per source rig.
WebGL bounds the actual framebuffer; native Vulkan recreates its offscreen worker
at the selected square resolution. These are **starting points, not measured i5
profiles**, and do not reduce the head's mesh/texture complexity or TTS model size.

While playing, choose **Observe 10 seconds of playback**. A JSON report uses actual
render observations (at least 20 playing frames); a conservative heuristic may
recommend Low. Apply it with **Apply measured recommendation**. Reports distinguish
WebGL submission cost from native response latency, and are not physical AV,
hardware-GPU timing or laptop acceptance. Paused time is excluded from samples.
Do not change settings during the observation. Download and inspect before sharing.

## Articulation calibration

Studio defaults to **Clear**; **Baseline** reproduces the old sampler and **Soft**
is gentler. Adjustable closure, F/V contact, tongue, jaw, rounding and transition
controls are presentation-only: the actual WAV/text-bound cues remain immutable.
Clear boosts estimated P/B/M closure from 0.95 to 0.9975, with stronger contact and
tongue poses and 35 ms smoothstep transitions. JavaScript/Python samplers agree
across all profiles, cue boundaries and end-rest. Native receives the same bounded
calibration as WebGL. Baseline remains available for comparing earlier recordings.

This is useful rig calibration, **not** independently verified phoneme timing,
proof of physical lip/teeth contact, or human-reviewed articulation/naturalness.
Review the same recordings on your display and adjust conservatively.

## Verified audio prebuffer and longer paragraphs

Sentence mode now permits **1,000 input characters / 12 chunks**, retaining
160 characters per synthesis chunk, two pending producer chunks and 60 seconds
of actual PCM. Whole-utterance mode remains 500 characters. Producer backpressure,
WAV/cue/rig binding, sample offsets and cancellation remain enforced.

**Prebuffer next audio** downloads, hashes and primes up to two available upcoming
chunks before handoff. Stop/cancel owns and disposes the requests and blob URLs;
late responses cannot restore an old performance. The stream report includes
prebuffer hits, downloaded-ahead counts and observed handoff gaps. Turn prebuffer
off to compare. The controlled local browser test adds **120 ms per WAV request**
and checks that prefetched playback reduces handoff gaps by at least 50 ms.
This is synthetic transport evidence, not a claim about neural synthesis speed.
It is still sentence-batched Kokoro, **not guaranteed gapless or internally
incremental inference**; production underruns and prosody changes remain possible.

## Windows launcher, diagnostics and recovery

After existing source setup, double-click **`windows/launch-studio.cmd`**, or run:

```powershell
.\windows\launch-studio.ps1
```

Choose WebGL/native Vulkan and a starting preset, then **Launch studio**. A free
loopback port avoids the previous fixed-port conflict. **Stop studio** or closing
the launcher stops only its owned process tree. No downloads, elevation or silent
renderer fallback are performed. Native still requires explicit native setup.

A newly built personal `JaliStudio.exe` opens the same chooser on double-click.
The frozen command-line server remains available with `--serve`; existing server
flags also continue to work. **Run diagnostics** checks pinned assets and can
perform a real small native readback. Missing files/driver failures include repair
steps and an explicit WebGL alternative. Logs and diagnostics are saved under
`%LOCALAPPDATA%\JaliVulkan`; inspect paths/errors before sharing.

```powershell
.\JaliStudio.exe --doctor
.\JaliStudio.exe --doctor --native
.\JaliStudio.exe --verify-installation
```

A damaged frozen installation refuses the native device probe. Restore the whole
trusted package into a new empty directory; never fetch random DLLs or disable
security. The build remains **unsigned/personal-only**, with existing GPL/eSpeak
corresponding-source and redistribution gates unresolved. No executable/weights
are published by CI.
