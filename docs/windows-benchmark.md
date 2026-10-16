# One-command Windows benchmark, M3 references and M4 preflight

**2026-10-16.** Benchmark collection is implemented. Articulation quality and the
rich native Vulkan port are **not** declared complete by collecting a report.

## 1. Run the benchmark on your laptop

Complete [Windows developer setup](windows-neural-studio.md) first. The benchmark
does not install dependencies, fetch models, require payment, or upload anything.
From the repository in PowerShell:

```powershell
.\windows\benchmark.ps1
```

Default: installed **Chrome**, visible window, **two repeats of three public
sentences** (six fresh CPU recordings). Keep that window visible; do not seek,
resize, pause, change speed or switch tabs. Current Edge is an explicit option:

```powershell
.\windows\benchmark.ps1 -Browser msedge -Repeats 2 -Conditions 'Plugged in; Balanced; other apps closed; Chrome/Edge version ...'
```

Normal laptop use should not set `-Headless`. That switch is for automated
hosted tests; CI permits software fallback and cannot establish laptop GPU FPS.
The run may take several minutes. Ctrl+C attempts cleanup and records cancellation;
this is not a general streaming/interruption implementation.

### What to save

**`artifacts/jali-benchmark-report.json`** is the single shareable report. Inspect
it before sharing: it contains OS/CPU/RAM/graphics information, browser renderer
strings and your optional conditions. It excludes serial numbers, environment
variables, arbitrary process inventories, logs and automatic uploads. Logs may
contain local file paths: do not blindly share the whole run directory.

Every invocation keeps its own report, public WAVs, clip manifests, empty reference
templates and local logs under `artifacts/benchmarks/<run-id>/`. No prior run is
deleted. Disk usage therefore grows; remove unwanted benchmark run folders after
preserving anything you want. The benchmark uses an **isolated session store and
ephemeral loopback port**, so it does not clear an interactive studio's recordings.
The interactive server now binds before clearing its store; a busy port must not
delete the existing instance's sessions. Windows uses exclusive port binding.

### Report interpretation

- `status: completed` means **collection completed**, not “fast enough”, good
  articulation or successful target-device acceptance. Failed/cancelled runs are
  not reported as completed; partial measurements are retained separately.
- Server readiness includes startup asset checks. Browser readiness is page/face
  readiness **after browser launch**, not OS/browser cold-start latency.
- Per request: dependency imports, engine/model/voice/tokenizer loading, waveform
  generation, real-time factor, exact-WAV/dialog analysis and total pipeline time.
- Peak speech-worker memory is Windows peak working set or Linux high-water RSS.
  It excludes the server, browser/GPU, other processes and total app RAM.
- Browser canvas dimensions/pixel ratio, renderer/vendor, frame gaps and CPU-side
  render submission costs are recorded for the exact new recording.
  Legacy fields `rendered_frames` / `observed_render_fps` count **renderer update
  submissions**, not verified presented/display frames, GPU execution or physical
  speaker/display AV latency. A 30 fps target is not a measured 30 fps result.
- Every request starts a fresh speech worker. Later repetitions may benefit from
  OS/file caches; they are **not** a warm persistent inference worker. First request
  is not proof of reboot-cold behavior. Two short runs cannot establish p95 overall
  generation latency, sustained thermal behavior, long-utterance drift or quality.
- No made-up score or performance threshold is used. Compare repeated like-for-like
  conditions before changing quality settings.

The Linux sandbox completed **six** fresh requests and browser samples, with no
external browser requests/errors. Its software renderer was slow (roughly 1–2
submitted updates/s); this is not a prediction for the laptop's integrated GPU.
The actual PowerShell launcher also passed on a Windows hosted runner in
[Actions run 38844926069](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38844926069),
source `358d4e3e7994d674393501d79d9bfd22e90df671`. All **nine jobs passed**.
Windows CI executed `windows/benchmark.ps1 -Repeats 1 -Headless` and required
three complete new CPU/browser samples, alongside the existing live pipeline.
The combined Windows job took **4m36s**; Linux integration took **3m36s**.
The full Linux suite passed **87 Python + 12 JavaScript tests**; the new benchmark,
reference and native-audit unit tests were also included in the Windows subset.

The hosted `windows-local-neural-evidence` artifact includes the Windows
`jali-benchmark-report.json`, with three-day retention. This sandbox verified the
job/step conclusions via API, not independently downloaded hosted artifact bytes.
[Hosted metadata](evidence/neural-benchmark-actions.json) and the separate
[six-sample Linux report](evidence/neural-benchmark-local.json) are retained.
Neither report is presented as results from the user's laptop.

## 2. M3: independent reference comparison, not self-scoring Rhubarb

Each sample writes `<case>-<repeat>.wav`, `-clip.json` and `-reference.json` in its
run folder. Reference templates deliberately have **no event times**, no reviewer,
no method and `independent_of_rhubarb: false`. Rhubarb cues are not copied into
reference labels. Pending templates are refused by the evaluator.

Listen to that exact WAV and inspect a waveform (or use a separately reviewed
independent aligner), then fill the reference with attributed source information.
Example **format only**, not a reference for any delivered recording:

```json
{
  "audio_sha256": "copy the actual WAV hash from this sample's template",
  "text_sha256": "keep this sample's original requested-text hash",
  "method": "manual-listening-waveform",
  "reviewer": "your chosen reviewer label",
  "source": "How you listened/marked the waveform; uncertainty rationale",
  "independent_of_rhubarb": true,
  "events": [
    {"start": 0.21, "end": 0.49, "class": "A", "uncertainty_seconds": 0.02}
  ]
}
```

**Do not copy those example times.** A–H/X are the existing nine mouth classes,
not literal phoneme labels: A P/B/M, G F/V, H L/tongue, C/D open vowels,
E/F rounded vowels, B other consonants/spread vowels, X rest. Their approximate
semantic grouping is itself an assumption to review. Mark non-overlapping windows
within the actual recording, and state your timing uncertainty (0–0.25 s).
Inspect lip closure/contact, teeth/tongue and whole-utterance transitions as well;
numerical timing agreement does not verify physical articulation.

After replacing the pending fields with real independent annotations:

```powershell
.venv\Scripts\python.exe tools/evaluate_articulation.py `
  --reference artifacts/benchmarks/RUN/closures-1-reference.json `
  --clip artifacts/benchmarks/RUN/closures-1-clip.json `
  --wav artifacts/benchmarks/RUN/closures-1.wav `
  --output artifacts/closures-1-comparison.json
```

The CLI checks actual WAV hash/duration, text hash, valid cue timeline, reference
source declarations, finite/non-overlapping intervals and uncertainty. Output
reports expected-class coverage **only in supplied windows**, signed onset/offset
error for the largest overlapping same-class cue, or null errors when no class
matches. It does not certify source independence: attribution is user-declared.
It does not manufacture a naturalness score, a full-utterance accuracy metric or
physical AV measurement. **No rig-strength tuning is declared validated yet.**

## 3. M4: actual native-profile blockers

Every report includes a static audit of the actual optimized GLB and the hash of
`src/character.cpp`. The current asset has **8 meshes, 8 skins, 7 materials,
7 images, 67 joints per largest skin and up to 66 morph targets**. The existing
native path rejects required extensions/materials, expects one mesh/skin, allows
64 joints and stores exactly three fixed named facial deltas. Signed quantized
accessors are also outside its supported reader types.

The audit records these blockers without modifying/truncating assets. It is a
partial metadata audit, **not native import or GPU rendering**. Next M4 work must:

1. Define a rich native asset/profile contract and decode Meshopt/quantization.
2. Preserve all instances, skin hierarchies, inverse binds and transforms.
3. Expand palette/shader/buffer ABI together; support named morphs on face and
   secondary meshes rather than renaming 66 shapes into three unrelated deltas.
4. Add UV/material/texture/color-space paths and correct normal handling.
5. Compare CPU deformation/canonical poses with WebGL, then run real Vulkan
   validation and connect the same audio/cue session identity.

Increasing a joint constant alone does not accomplish those steps. M4 remains
unimplemented for this head. M3 listening/visual review and actual laptop data
remain necessary; hosted CI does not close them.
