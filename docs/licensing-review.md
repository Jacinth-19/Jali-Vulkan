# Personal-build licensing review — 2026-10-16

## Decision and scope

This is an **engineering review and blocker register, not legal advice or a legal
clearance**. The supported delivery is your own local, unsigned personal build.
**Do not publish the bundle, installer, neural weights or a public release.**
Noncommercial intent alone does not exempt redistribution from license duties.
Code signing is optional for personal use and does not establish compliance.

Reviewed inputs: checked-in Python/Node pins, discovered installed distribution
metadata/notice paths, the prepared model/voice/character notices, native build
notice copying, package inclusion rules and release settings. The local inspection
covered the **31 pinned Python runtime distributions** in
`tools/requirements-local-neural.lock.txt`; this is not a claim that every
transitive binary's source, copyright or license has been independently audited.
`tools/release_inventory.py --output artifacts/license-inventory.json` records the
core installed package/model/voice inventory. The review must be repeated when
pins, packaging rules, imported assets or a compiler change.

## Component findings

| Component | Finding / handling |
|---|---|
| This repository's original code | No top-level LICENSE file was present in the reviewed checkout. A public source/binary licensing decision requires the owner's authority; no license was silently added or inferred. |
| Kokoro ONNX Python wrapper | Installed wrapper has a LICENSE file (despite missing top-level license metadata); upstream wrapper licensing must remain separate from the model's Apache-2.0 terms. |
| Kokoro q8 model and stock voices | Explicitly prepared checksum-pinned assets, with retained Apache-2.0 notices. Optional `af_bella`/`am_michael` are stock identities, not voice-00 or clones. Independent q8 identity/provenance comparison to the original upstream model remains open. A checksum establishes identity to the selected archive, not ownership or blanket rights. |
| ONNX Runtime | MIT metadata plus its own LICENSE and ThirdPartyNotices are discoverable. Those third-party notices remain relevant; do not replace them with a one-line MIT label. |
| NumPy | Installed metadata declares BSD-3-Clause, 0BSD, MIT, Zlib and CC0-1.0 terms, with component notices. It is not accurately described as a single BSD-only binary. |
| phonemizer-fork 3.3.2 | GPL-3.0 license text is present. Public combined-bundle corresponding source, build/install instructions and combined-work duties are unresolved. |
| espeakng-loader 0.2.4 / embedded eSpeak | No adequate license metadata or notice file was discovered in the installed distribution. Upstream eSpeak/source obligations need explicit fulfillment before distribution; a metadata copy is not a solution. |
| FlatBuffers | Metadata declares Apache 2.0, but no notice file was discovered in the installed distribution. Retain the appropriate upstream notice/license and review actual bundled components before release. |
| Pillow / remaining pinned Python distributions | Metadata/notice paths were inventoried; this does not establish complete source/notice fulfillment for every embedded library or wheel. The personal package retains collected metadata; public clearance remains open. |
| Rhubarb | Retains its full multi-component LICENSE, not only its MIT summary. Its dependencies/resources have their own included permissive terms. Estimated mouth classes are not independent phoneme truth. |
| Default MPFB head | The specific pinned asset is described as CC0 by its source; CC0 text and source README are retained. This does not license every avatar in that repository. |
| User-imported GLB / textures | A provenance/license declaration is required in the retarget profile. That declaration is not independently checked ownership or legal approval. Do not import assets you cannot use. |
| Three.js, Meshoptimizer, webm-muxer | Prepared runtime notice files are copied into the studio's licenses directory. Node build/test dependencies have separate package-lock pins and notices; they are not all browser runtime code. |
| Native Vulkan loader/headers and tinygltf | The personal native build copies the pinned dependency notices. No GPU driver is bundled. Other native/transitive notices still require distribution review. |
| imageio-ffmpeg / FFmpeg | Development evidence/MP4 decoding/encoding only. FFmpeg's actual binary configuration can impose additional duties; the wrapper license is not the binary license. **Excluded from the frozen runtime**, with a build guard rejecting leaked FFmpeg EXE/DLLs. Browser WebM export uses WebCodecs, not a bundled FFmpeg process. |
| PocketSphinx / browser automation / Node tools | Development crosscheck/build tools, not required on the user's runtime PATH. PocketSphinx is explicitly excluded from the personal frozen runtime. Test-tool artifacts are not a distributable app. |
| Inno Setup | Optional, locally installed compiler for the personal per-user installer. Review the exact compiler/version terms for other uses. No installer/compiler is uploaded by CI, and signing or a paid update service is not required. |

## Public-release blockers

1. Establish the owner's intended license/authority for the original repository.
2. Resolve GPL phonemizer/eSpeak combined-work obligations; provide complete
   corresponding source and appropriate build/install information and notices.
3. Resolve the espeakng-loader/FlatBuffers notice gaps and review the **actual
   frozen payload**, including native and Python third-party binaries, not just
   package metadata.
4. Independently resolve q8 model provenance/identity and all imported asset rights.
5. Recheck notices, source delivery, installer terms and release materials for the
   exact version being distributed. Keep release authorization false until done.

The machine-readable [release gates](release-gates.json) intentionally remain
blocked for public redistribution. Passing functional CI, making a noncommercial
version, buying a signing certificate, or generating an inventory does **not**
close these gates. None of these public-release tasks blocks building and testing
the scoped personal version described in [workspace upgrades](workspace-upgrades.md).
