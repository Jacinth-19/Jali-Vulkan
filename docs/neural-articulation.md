# M3: repeatable articulation review and hosted CPU validation

Status: **partial**, 2026-10-16. These checks exercise real generated speech and
real WebGL morphs. They do not complete perceptual or independently aligned QA.

## Timing defects corrected

- Transition blending is now limited to the final **35% of each estimated cue**,
  capped at 35 ms. Previously, a fixed 35 ms transition could dilute a whole
  10–30 ms P/B/M closure. The central target pose is now preserved.
- The **actual audio duration** forces the mouth to rest. Rounded cue endpoints
  and a negative manual timing trim cannot leave a talking pose at audio end.
- Nine JavaScript tests cover these cases, including short closures, invalid input,
  an empty live studio, and playback-end behavior. This verifies sampling, not
  phonetic correctness or physical speaker/display timing.

## Fixed public review corpus

`tests/fixtures/neural-articulation.json` supplies three deliberately short texts:
closures; lip/teeth and tongue contacts; and open/rounded/spread vowels.
Each request generates a new stock Kokoro `af_heart` CPU recording and analyzes
that exact recording with its dialog. No external fixture voice is impersonated.

The real browser test checks unique session IDs and waveforms, download hashes,
CPU execution, actual named morph weights, seek/replay, natural completion,
sync-off reset, mobile layout, browser errors and unexpected network requests.
In review mode it additionally captures neutral, motion-disabled 512px PNGs at
estimated cue midpoints. It records missing classes rather than pretending all
classes must occur in every sentence.

A local execution produced **22 frames covering all nine estimated classes**,
three new WAVs, and a 15 fps offline MP4 of the first new recording. Complete
text-to-analysis time was 11.53–14.98 seconds for 3.46–4.07 seconds of audio.
These are this sandbox's CPU timings, not target-laptop benchmarks.

## Run and inspect

After following [the studio setup](neural-studio.md), with a server already running:

```sh
JALI_REVIEW=1 EXPORT_VIDEO=1 node tools/smoke_neural_studio.cjs
```

For the disposable hosted-style check, **stop an interactive studio server first**:

```sh
.venv/bin/python tools/run_neural_ci.py
```

The latter starts a bounded disposable server on port 8082, runs the real browser,
collects only the exact public corpus, and stops its own server even on failure.
It refuses an occupied port. A server startup clears earlier session directories;
copy any wanted recordings first. Do not use a development workspace containing
private recordings for automated public artifact collection.

Extract the generated `artifacts/neural-review/` directory completely and open
`index.html`. It pairs audio with estimated mouth-class PNGs and review questions.
`articulation.json`, `browser-check.json`, session manifests, requested text,
actual WAVs, cue JSON and `video-export.json` retain provenance. Models, caches,
access tokens and arbitrary sessions are not part of this review artifact.
The MP4 is offline capture, **not** a real-time rendering benchmark.

## GitHub Actions coverage

The `neural-studio` job in `.github/workflows/ci.yml` uses the standard hosted
Ubuntu 24.04 CPU runner, Python 3.11, Node 22 and pinned dependency versions.
It explicitly prepares checksum-pinned Kokoro/voice/analyzer assets and the
pinned CC0 character; then runs the Python and JavaScript suites and actual
model/browser review. Setup failures are also emitted as check annotations.
The runner's actual CPU, memory and disk inventory is recorded.

It runs on pushes to this session's branch and manual workflow dispatch, not
untrusted pull requests. Permissions are read-only, action versions are commit
pinned, execution is bounded to 20 minutes, and synthetic review artifacts expire
after three days. No larger/GPU runner or paid hosted speech service is requested;
normal GitHub account quotas still apply. Actions is a test environment, not an
always-on product host.

The earlier native/eSpeak Actions success does **not** establish neural coverage.
Fresh neural hosted results are recorded separately when actually completed.

**Passed:** [Actions run 38837436553](https://github.com/Jacinth-19/Jali-Vulkan/actions/runs/38837436553),
source commit `0680866bb2fdd82fa3d988d540b48eadf68417c2`. All **seven jobs**
passed. The real neural speech/WebGL job took **3m22s**, including cold setup,
67 Python tests, nine JavaScript tests, three new corpus recordings, actual audio
analysis, browser checks, neutral review images and MP4 export. Resource inventory
and review media are in its `neural-articulation-review` artifact (three-day
retention). API-verified job/artifact metadata is retained in
[`evidence/neural-articulation-actions.json`](evidence/neural-articulation-actions.json).

The initial hosted attempts failed in cold character download: the hosted `gh`
CLI could not transport a raw binary response (`transform: short source buffer`).
The fix fetches JSON/base64 through the contents/blob APIs and decodes it in
Python, preserving the pinned 36,815,920-byte source character hash. Four new
admission tests cover binary-byte preservation and invalid metadata. Our cached
local build had not exercised this cold-download path. The successful run above
is after the fix; failed setup attempts are not counted as neural validation.

## Open quality gates

- `human_review_completed: false`, `independently_verified_phoneme_alignment: false`
  and `quality_score: null` are intentional, not missing calculations.
- A P/B/M weight assertion cannot establish visible lip sealing. F/V and L shapes
  still need contact/penetration review; rounded/spread vowels need comparison.
- Midpoint PNGs cannot establish natural transitions or word/sound alignment.
  Listen to the recordings and review full-utterance video before rig-strength tuning.
- We have not established an independent phoneme reference, forced alignment,
  long-utterance drift, physical AV latency, Windows speed or hardware-GPU FPS.
- The detailed character remains in WebGL; richer native Vulkan support is M4.
