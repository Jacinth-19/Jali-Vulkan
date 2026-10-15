#!/usr/bin/env python3
"""Opt-in local Chatterbox adapter. No model download, built-in identity, or demo fallback.

Not enabled in the preview. Requires an operator-reviewed grant, matching reference,
reviewed local checkpoints, and a separately installed Chatterbox runtime. Unit tests
exercise admission checks; actual neural synthesis has NOT been validated here.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import wave

FILES = ('ve.safetensors', 't3_cfg.safetensors', 's3gen.safetensors', 'tokenizer.json')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_grant(manifest):
    manifest = Path(manifest).resolve()
    grant = json.loads(manifest.read_text())
    if not isinstance(grant, dict) or grant.get('schema') != 1:
        raise ValueError('Unsupported voice grant schema')
    for field in ('consent_id', 'subject_id'):
        if not isinstance(grant.get(field), str) or not grant[field].strip():
            raise ValueError(f'Missing {field}')
    scopes=grant.get('scopes')
    if grant.get('status') != 'active' or not isinstance(scopes,list) or 'local-voice-synthesis' not in scopes:
        raise ValueError('Voice grant is revoked, inactive, or out of scope')
    expiry = datetime.fromisoformat(grant['expires_at'].replace('Z', '+00:00'))
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError('Voice grant is expired or lacks a timezone')
    reference_info = grant['reference']
    reference = (manifest.parent / reference_info['path']).resolve()
    if sha256(reference) != reference_info['sha256']:
        raise ValueError('Reference audio differs from the authorized recording')
    with wave.open(str(reference), 'rb') as audio:
        count, rate = audio.getnframes(), audio.getframerate()
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != 'NONE' or not 16000 <= rate <= 48000 or not 3 <= count/rate <= 30:
            raise ValueError('Reference must be 3-30 seconds of mono PCM16 WAV at 16-48 kHz')
        if len(audio.readframes(count)) != count*2:
            raise ValueError('Truncated reference WAV')
    model = grant['model']
    if model.get('license_reviewed') is not True:
        raise ValueError('Checkpoint license review has not been acknowledged')
    directory = (manifest.parent / model['directory']).resolve()
    if (directory / 'conds.pt').exists():
        raise ValueError('Remove optional pickled conds.pt; condition only on the approved recording')
    for filename in FILES:
        expected = model.get('sha256', {}).get(filename, '')
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected) or sha256(directory / filename) != expected:
            raise ValueError(f'Unreviewed/mismatched model artifact: {filename}')
    return grant, reference, directory


def synthesize(manifest, text, output, device='cpu'):
    if device not in ('cpu', 'cuda') or not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 240 or '\0' in text:
        raise ValueError('Invalid device/text; synthesis is limited to 240 UTF-8 bytes')
    grant, reference, directory = validate_grant(manifest)
    # Import only after authorization and artifact checks. Never invoke from_pretrained.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from chatterbox.tts import ChatterboxTTS
    import torch
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA was required but is not available; refusing a hidden CPU fallback')
    model = ChatterboxTTS.from_local(directory, device=device)
    audio = model.generate(text, audio_prompt_path=str(reference))
    # Revocation/expiry/reference changes during a long inference invalidate the output.
    current, _, _ = validate_grant(manifest)
    if current != grant:
        raise ValueError('Voice grant changed during synthesis')
    if audio.ndim not in (1,2) or (audio.ndim == 2 and audio.shape[0] != 1):
        raise ValueError('Neural provider must return mono PCM')
    values = audio.detach().cpu().reshape(-1)
    rate = int(model.sr)
    if not 8000 <= rate <= 192000 or not 0 < values.numel() <= rate*60 or not torch.isfinite(values).all():
        raise ValueError('Neural provider returned invalid/excessive audio')
    pcm = (values.clamp(-1, 1)*32767).round().to(torch.int16).numpy().astype('<i2').tobytes()
    output = Path(output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output.parent, suffix='.wav')
    os.close(fd)
    try:
        with wave.open(temporary, 'wb') as stream:
            stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            stream.writeframes(pcm)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    provenance = {'synthetic': True, 'provider': 'chatterbox-local', 'consent_id': grant['consent_id'],
                  'reference_sha256': grant['reference']['sha256'], 'model_sha256': grant['model']['sha256'],
                  'watermark': 'provider-default-not-independently-verified',
                  'alignment': 'not-generated-do-not-reuse-espeak-timings'}
    output.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--text', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    args = parser.parse_args()
    synthesize(args.manifest, args.text, args.output, args.device)


if __name__ == '__main__':
    main()
