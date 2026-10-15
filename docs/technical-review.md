# Technical review: voice–face pipeline

Reviewed: **2026-10-15**. Scope: the supplied architecture report and a feasible first implementation for this previously empty repository.

**Status note:** this review was written for the original mock/headless baseline. The subsequently implemented optional eSpeak NG and procedural Vulkan backends are documented in [running the demo](running-demo.md), including their additional dependency licenses and remaining limits. Baseline-only statements below are not claims that these backends are still absent.

## Executive decision

Keep the modular C++ architecture, timestamped audio/animation data, glTF-first asset pipeline, and deterministic CI gauntlet. **Do not treat the original comparison tables, latency figures, or legal statements as verified requirements.** Several mix up products, code and model licenses, and file-format limits versus engine implementation policies.

Start with a dependency-free, offline, headless contract test. Add real providers, asset I/O, and Vulkan only behind separately tested adapters. A passing synthetic fixture is not evidence of speech intelligibility, natural facial animation, actual playback synchronization, or GPU correctness.

## Corrections that affect implementation

| Original assertion | Correction / decision | Evidence or validation needed |
|---|---|---|
| Chatterbox is a Rust/C++ backend with tiny models, emerging in 2024 | The checked upstream project is Python/PyTorch-based. Its MIT license carries a 2025 copyright. Current variants have different size and latency characteristics; the upstream README describes Turbo as 350M parameters. Plan a local service adapter, not an assumed native C++ API. | [S1] |
| Coqui / XTTS is simply MPL-2.0 and therefore available for commercial use | Separate the TTS **code** license (MPL-2.0) from checkpoint rights. The upstream model registry labels XTTS v2 **CPML**. Review the exact weights' terms and commercial rights before distribution or service use. Do not describe repository popularity as proof of current maintenance. | [S2] |
| OpenVoice uses Apache-2.0 | Upstream identifies V1 and V2 as **MIT**. Independently inventory any base TTS models, vocoders, checkpoints, and datasets used alongside it. | [S3] |
| Bark is a JAX/TPU model and necessarily batch-only | The checked implementation imports PyTorch. Its README says roughly real-time generation is possible on some enterprise GPUs, but that is not a streaming guarantee. It also warns of deviation from text prompts. Do not use it as the deterministic transcription baseline or assume exact speaker cloning. | [S4] |
| Meta Voicebox is an Apache-licensed public Tacotron/Flowtron toolkit; “FlutterVoice (Magenta)” is a candidate library | These product identities and availability are not established by the report. Remove both from the engineering shortlist until an official repository, model card, license, and usable API are supplied. A failed repository lookup alone is not proof a project does not exist. | Unverified; no implementation dependency |
| TTS, voice conversion, and cloning are interchangeable | Keep separate capabilities: text-to-speech, speech-to-speech conversion, speaker conditioning, streaming output, and alignment/timing output. RVC-style conversion needs input speech; it is not a standalone text-to-speech stage. | Provider contract / integration test |
| Real-time means synthesizing an entire utterance in <100 ms; commercial latency figures are guarantees | Measure **time to first playable audio**, real-time factor (generation time / audio duration), steady-state chunk cadence, jitter, and end-to-end p50/p95 latency independently. Published model numbers depend on hardware, region, settings, buffering, and metric definitions. No 75 ms or 200 ms production promise is adopted. | Reproducible deployment benchmark |
| ARKit has 52 visemes and a standard phoneme mapping | ARKit facial coefficients describe expressions and facial motion, not a canonical 52-phoneme/viseme vocabulary. A rig-specific retarget layer is still required. Audio-driven facial motion and camera-based facial capture are separate input paths. | Validate channel names against the selected Apple SDK and capture device before implementation |
| Audio2Face is uniformly open source and directly portable to any C++/ONNX runtime | The checked NVIDIA overview distinguishes MIT SDK code, Apache training code, NVIDIA Open Model weights, restricted emotion models, evaluation-only sample data, and separately licensed NIM packaging. Integration and GPU/runtime portability depend on the exact package. Do not equate an ONNX artifact with a verified portable inference graph. | [S5] |
| Live Link Face is Apple's app; FaceFX is “by Unity”; all capture tools have the listed prices and release years | Separate Apple ARKit from Epic's Live Link Face app/Unreal workflow. Remove the unsupported FaceFX ownership attribution. Do not adopt the report's pricing, release-year, export-format, platform, or live-inference claims without checking the selected vendor version. | Vendor due diligence; not independently reverified here |
| Blender Rigify has no default face rig | This is version-dependent and should not be used to exclude Rigify. Evaluate the actual Blender/Rigify version's face components and bake/export behavior. | DCC fixture acceptance test |
| glTF supports at most four joint influences per vertex | `JOINTS_0`/`WEIGHTS_0` each supply four entries. Additional sets such as `JOINTS_1`/`WEIGHTS_1` support additional influences. **This starter deliberately accepts at most four**, an engine policy rather than a format limitation. Reject or explicitly reduce larger inputs with an error report; never silently truncate them. | [S6] |
| glTF supports at most eight blendshapes per primitive | The specification explicitly says the number of morph targets is not limited. Its implementation recommendation concerns at least **eight morphed attributes**, not a universal eight-target ceiling. Budget active targets and bandwidth in the engine. | [S6] |
| Morph weights must always be in [0,1] | This is a useful policy for a normalized `jawOpen` channel, not a universal constraint on every corrective/expression control. Define allowed ranges per rig channel. Reject NaNs/infinities and out-of-policy values. | Rig contract; [S6] |
| Assimp is “BSD/MIT”; glTF export is partial and FBX universally experimental | Assimp's checked license is BSD-3-Clause. The checked exporter registry includes `gltf2`, `glb2`, `fbx`, and `fbxa`; presence does not guarantee fidelity. Broad maturity labels cannot replace version-specific round-trip tests. Native DCC/format-aware exporters may preserve more intended rig semantics. | [S7] |
| glTF is ISO 12113:2022 | Correct identifier: **ISO/IEC 12113:2022**. glTF is right-handed, Y-up; coordinate, winding, tangent, and unit conversion must be explicit. | [S6]; ISO designation should be confirmed in release/legal documentation |
| “Khronos glTF SDK” is Microsoft's official Khronos C++ SDK | Microsoft glTF-SDK is a Microsoft MIT-licensed project, distinct from Khronos's specification and validator. tinygltf is another loader/writer; “no dependencies” is not a safe blanket description. Inventory the chosen revision and bundled parser/image components. | [S8], [S9] |
| Compute skinning always scales better and automatically serves physics/ray tracing | Choose compute versus vertex deformation by measured pass count, geometry, bandwidth, and hardware. Compute output is useful only with correct buffer usages, visibility barriers, lifetimes, and downstream acceleration-structure or collision updates. CPU physics does not get free synchronous access to a GPU buffer. | Vulkan integration acceptance tests |
| A bone palette can just be passed in push constants | Full palettes commonly exceed push-constant capacity. Use SSBOs or suitably sized UBOs. Query device limits; reserve push constants for small draw parameters and offsets. | Device-limit checks |
| Hosted Actions runners always have 2 CPUs / 7 GB; larger runners are beta; a low-privilege container is a security boundary | Runner resources, availability, billing, and limits depend on repository, OS, plan, and runner class. Avoid stale constants. Shared self-hosted runners are dangerous for untrusted PRs; containers are not a substitute for isolation or restricted credentials. | Check current GitHub runner documentation when provisioning |
| Actions automatically provides safe training and model caching | Use short-lived isolated GPU runners, trusted workflow inputs, immutable code/model references, protected approval environments, and scoped credentials. Never run fork PR code on a persistent privileged GPU host. Do not put private recordings or licensed checkpoints in broadly accessible caches/artifacts. | CI threat model and access review |
| Voice recordings are always GDPR biometric special-category data; consent alone ensures legality; the ELVIS Act is only a commercial-use ban | These are overbroad legal summaries. Recordings can be personal data; special-category biometric treatment depends on processing and purpose. Applicable identity, privacy, disclosure, retention, publicity, and contract rules vary by jurisdiction. Consent is necessary in many uses but not a universal legal defense. Obtain jurisdiction-specific advice, including for Ghana deployments where applicable. | Legal review; not legal advice |
| A watermark or prefix guarantees safe synthetic audio | Metadata/disclosure and robust watermarking are distinct mechanisms. Watermarks can be lost or undetectable after transformations and cannot prove permission. Preserve a consent/license reference, model provenance, retention policy, and revocation workflow independently. | Threat model / provider verification |
| Protoface references [20], [54], and line-number citations establish the QA method | The supplied report contains no resolvable bibliography for these references. Do not rely on them. Specify the test algorithm and its limitations directly. | Local implementation and tests |

## Revised shortlist (not a procurement endorsement)

Quality is intentionally not ranked without a shared evaluation corpus and hardware. GPU use, streaming support, commercial rights, and checkpoint license must be verified for **each selected version**.

| Role | Candidate | Integration approach | License / operational decision |
|---|---|---|---|
| First runnable fixture | Local mock source | C++ tone generator + PCM buffer | No model, real identity, credentials, or network |
| Local TTS experiment | Chatterbox | Separate pinned Python/PyTorch worker with bounded IPC | MIT project; review all deployed artifacts; benchmark chosen variant [S1] |
| Alternative multilingual TTS | XTTS | Separate Python worker | MPL-2.0 code versus CPML checkpoints; commercial clearance required [S2] |
| Tone-color / speaker conversion experiment | OpenVoice | Python adapter plus explicitly selected base TTS | MIT project; review component and data rights [S3] |
| Expressive offline experiment | Bark | Python/PyTorch tool, not the CI oracle | MIT project; prompt deviation and deployment performance caveats [S4] |
| Cloud TTS / authorized cloning | ElevenLabs, Resemble, Azure | Swappable service adapter with cancellation, timeout, retry budget, disclosure, and authorization checks | Proprietary terms; no API key or vendor lock-in added to this starter |
| Baseline face animation | RMS envelope | C++ `jawOpen` curve | Diagnostic motion only; no phoneme awareness |
| Higher-fidelity audio-to-face | Audio2Face-3D | Exact SDK/model/runtime combination behind mapper | Package-specific licenses and deployment constraints [S5] |
| Asset interchange | Assimp + glTF Validator | Optional import/export worker and round-trip fixtures | BSD-3-Clause Assimp; validator as independent gate [S7], [S10] |
| Focused glTF I/O alternative | tinygltf / Microsoft glTF-SDK | Consider if Assimp loses needed semantics | MIT projects; review dependencies [S8], [S9] |
| Native inference | ONNX Runtime / vendor runtime | Add only after model compatibility spike | No automatic conversion or cross-vendor portability assumption |

Capture/DCC tools are deliberately deferred until there is a consented, known-good rig and a target device. Do not introduce a dozen vendor dependencies merely to reproduce the report's table.

## Corrected QA interpretation

Onset error is a useful **transport and timestamp smoke test**, not a lip-sync quality metric. Mouth motion naturally may precede audible phonation, and plosives can involve closed lips. A single onset measurement misses drift, incorrect phonemes, frozen poses after onset, coarticulation, and pose-specific deformation failures.

The starter gates absolute signed onset error: `abs(face_onset - audio_onset) <= tolerance`. It rejects missing signals rather than treating silence as a pass. Energy uses approximately 10 ms windows; the mouth threshold and energy threshold are intentionally different. This resolution is a measurement limit, not a sub-millisecond accuracy claim.

The mock face curve is derived from the same audio envelope that the analyzer measures. **An aligned result is expected by construction.** Negative tests that introduce leads, delays, missing signals, invalid weights, bad hierarchy links, and malformed artifacts establish that the gate can reject errors. They do not establish real-world animation quality.

Later gates must use actual playback/device timestamps and presented frames, test synchronization across the whole utterance, and incorporate independently authored expected cues and human review. Capture real rendered motion rather than trusting only the curve sent to the renderer.

## Legal, privacy, and dependency release gates

Before a real voice provider is enabled:

- Obtain documented authorization for each voice and source recording, with permitted uses, expiration, revocation, and deletion policy.
- Keep a bill of materials covering **code, weights, datasets, vocoders, runtime packages, and generated-content terms**.
- Reject requests whose authorization is absent, revoked, expired, or out of scope. The mock accepts only `synthetic-fixture`; it is not a completed consent system.
- Keep sensitive audio out of public artifacts, logs, caches, and Git. Encrypt approved storage, restrict access, and implement retention/deletion separately from logs.
- Preserve provider watermarking where applicable, disclose synthetic output, and record provenance. Do not implement a fake “watermark” claim using a JSON flag.
- Add quotas, timeout/cancellation, response-size bounds, schema validation, and restricted network access. Treat third-party model code as executable supply-chain input.

No voice models, consented recordings, cloud keys, face photographs, or third-party assets are added in this implementation. No project distribution license is selected on the owner's behalf.

## Evidence and limits

Primary GitHub sources below were inspected during this review. Pinned links identify the reviewed upstream revisions; these are evidence references, not dependencies downloaded by the build. Provider SaaS pages, Apple SDK documentation, current runner-plan quotas, and legal texts were **not independently retrieved** in this sandbox. Their claims remain deployment/release checks rather than asserted current facts. No measured latency or vendor quality ranking is claimed.

- **[S1] Chatterbox:** [manifest](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/pyproject.toml), [README](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/README.md), [MIT license](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/LICENSE).
- **[S2] Coqui TTS:** [README](https://github.com/coqui-ai/TTS/blob/dbf1a08a0d4e47fdad6172e433eeb34bc6b13b4e/README.md), [model registry with XTTS CPML labels](https://github.com/coqui-ai/TTS/blob/dbf1a08a0d4e47fdad6172e433eeb34bc6b13b4e/TTS/.models.json).
- **[S3] OpenVoice:** [README](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/README.md), [license](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/LICENSE).
- **[S4] Bark:** [README](https://github.com/suno-ai/bark/blob/f4f32d4cd480dfec1c245d258174bc9bde3c2148/README.md), [PyTorch inference implementation](https://github.com/suno-ai/bark/blob/f4f32d4cd480dfec1c245d258174bc9bde3c2148/bark/generation.py).
- **[S5] NVIDIA Audio2Face-3D:** [package, model, and dataset licensing overview](https://github.com/NVIDIA/Audio2Face-3D/blob/4d61b6b81ad7b5108512ea0eab10d8712ea4a236/README.md).
- **[S6] Khronos glTF 2.0:** [specification, especially morph targets and skinned mesh attributes](https://github.com/KhronosGroup/glTF/blob/521a91d491f02bb7db7d445b35f591d09d2a64ce/specification/2.0/Specification.adoc).
- **[S7] Assimp:** [license](https://github.com/assimp/assimp/blob/3e9c4e1d38a8cf4cbc63513e0f23a58f70833e49/LICENSE), [exporter registry](https://github.com/assimp/assimp/blob/3e9c4e1d38a8cf4cbc63513e0f23a58f70833e49/code/Common/Exporter.cpp), [glTF2 exporter implementation](https://github.com/assimp/assimp/blob/3e9c4e1d38a8cf4cbc63513e0f23a58f70833e49/code/AssetLib/glTF2/glTF2Exporter.cpp).
- **[S8] Microsoft glTF-SDK:** [repository](https://github.com/microsoft/glTF-SDK) and [license](https://github.com/microsoft/glTF-SDK/blob/master/LICENSE) (moving references).
- **[S9] tinygltf:** [repository README and license/dependency notes](https://github.com/syoyo/tinygltf) (moving reference).
- **[S10] Khronos glTF Validator:** [repository](https://github.com/KhronosGroup/glTF-Validator) (planned gate; not installed or run in this starter).
