#!/usr/bin/env python3
"""Explicit, checksum-pinned setup. Downloads assets, never executes npm code.

The standard model host and GitHub release download redirects are not reachable
in this sandbox. Use the declared npm redistribution of the Apache-2.0 ONNX
model, and the original kokoro-js package for its stock voice tensor.
"""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from urllib.request import urlopen

from runtime_paths import ASSET_ROOT as ROOT
ASSETS = ROOT / 'models/kokoro'
MODEL_SHA = 'fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478'
VOICE_SHA = 'd583ccff3cdca2f7fae535cb998ac07e9fcb90f09737b9a41fa2734ec44a8f0b'
PACKAGES = {
    'weights': {
        'url': 'https://registry.npmjs.org/kokoro-q8-shards/-/kokoro-q8-shards-1.0.0.tgz',
        'integrity': 'KoJQ203LxUOFrHAm12mu+hRmvqTmOcCgz61OVgTxmxX4isWaufLCF6kYz+QwOzVFYGNS62HHJWBHUbhzeoR43g==',
    },
    'voice': {
        'url': 'https://registry.npmjs.org/kokoro-js/-/kokoro-js-1.2.1.tgz',
        'integrity': 'oq0HZJWis3t8lERkMJh84WLU86dpYD0EuBPtqYnLlQzyFP1OkyBRDcweAqCfhNOpltyN9j/azp1H6uuC47gShw==',
    },
}


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def archive(name):
    metadata = PACKAGES[name]
    cache = ROOT / '.cache/local-neural'
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f'{name}-verified.tgz'
    if not target.exists():
        partial = target.with_suffix('.part')
        total = 0
        with urlopen(metadata['url'], timeout=90) as source, partial.open('wb') as output:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                total += len(block)
                if total > 130 * 1024 * 1024:
                    raise ValueError('Unexpectedly large model archive')
                output.write(block)
        partial.replace(target)
    sha = hashlib.sha512()
    with target.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(block)
    if base64.b64encode(sha.digest()).decode() != metadata['integrity']:
        raise ValueError(f'Archive integrity mismatch: {name}')
    return target


def member(bundle, name, maximum):
    info = bundle.getmember(name)
    if not info.isfile() or not 0 < info.size <= maximum:
        raise ValueError(f'Unexpected archive member: {name}')
    return bundle.extractfile(info)


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    licenses = ASSETS / 'licenses'
    licenses.mkdir(exist_ok=True)
    model = ASSETS / 'model_quantized.onnx'
    if not model.exists() or digest(model) != MODEL_SHA or not (licenses / 'model-redistribution-README.md').is_file():
        partial = model.with_suffix('.part')
        with tarfile.open(archive('weights')) as bundle, partial.open('wb') as output:
            for index in range(6):
                with member(bundle, f'package/kokoro-q8.part{index}.bin', 20 * 1024 * 1024) as source:
                    shutil.copyfileobj(source, output)
            with member(bundle, 'package/README.md', 100000) as source:
                (licenses / 'model-redistribution-README.md').write_bytes(source.read())
        if digest(partial) != MODEL_SHA:
            raise ValueError('Assembled ONNX model hash mismatch')
        partial.replace(model)
    # Extract exact files only; no npm install hooks, package code or arbitrary tar paths.
    with tarfile.open(archive('voice')) as bundle:
        for source, target, maximum in (
            ('package/voices/af_heart.bin', ASSETS / 'af_heart.bin', 600000),
            ('package/LICENSE', licenses / 'Kokoro-Apache-2.0.txt', 50000),
            ('package/README.md', licenses / 'kokoro-js-README.md', 100000),
        ):
            with member(bundle, source, maximum) as data:
                target.write_bytes(data.read())
    if digest(ASSETS / 'af_heart.bin') != VOICE_SHA:
        raise ValueError('Stock voice tensor hash mismatch')
    manifest = {
        'model': 'Kokoro-82M v1.0 ONNX q8, onnx-community export',
        'original_model_url': 'https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX',
        'code_and_voice_source': 'https://github.com/hexgrad/kokoro',
        'model_sha256': MODEL_SHA, 'stock_voice': 'af_heart', 'voice_sha256': VOICE_SHA,
        'license': 'Apache-2.0 as declared by Kokoro/kokoro-js and the model redistributor',
        'license_review_scope': 'Reviewed upstream GitHub Apache-2.0 license, npm package LICENSE/README and explicit model redistribution declaration. HF model card was not directly fetched here.',
        'packages': PACKAGES,
        'not_cloning': True,
        'note': 'Package integrity and assembled hash verified; no independent byte comparison with an unreachable upstream model host is claimed.',
    }
    (ASSETS / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Prepared {model.stat().st_size:,}-byte model and 522,240-byte stock voice tensor in {ASSETS}')


if __name__ == '__main__':
    prepare()
