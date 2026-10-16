#!/usr/bin/env python3
"""Analyze the existing stock WAVs with pinned CPU Rhubarb, not eSpeak retiming.

The result is dialog-guided estimated A-H/X mouth cues, NOT independently
verified phoneme-level forced alignment. No neural model or voice is synthesized.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

from neural_platform import analyzer_profile, analyzer_path, archive_relative
from urllib.request import urlopen

from build_test_pack import REFERENCES, ROOT, audio_metadata

ARCHIVE_URL = 'https://registry.npmjs.org/rhubarb-lip-sync/-/rhubarb-lip-sync-0.0.1-alfa-3.tgz'
ARCHIVE_SHA = 'd797623611a61b7e0c7f2c2e6f4c5c79eec2325f4447c6aaebb037083c082239'
BINARY_SHA = '03e82c9c76c4e691a058f38a9cf7e75331e2f3c31a9c1fab90c00944b3ef7dc2'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_timeline(data, duration):
    if not math.isfinite(duration) or not 0 < duration <= 60 or not math.isfinite(data['metadata']['duration']) or abs(data['metadata']['duration'] - duration) > 0.025:
        raise ValueError('Cue duration does not match the actual WAV')
    cues = data['mouthCues']
    if not isinstance(cues, list) or not 1 <= len(cues) <= 10000:
        raise ValueError('Invalid cue count')
    previous = 0
    for cue in cues:
        start, end = cue['start'], cue['end']
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or abs(start - previous) > 0.025 or end > duration + 0.025 or cue['value'] not in set('ABCDEFGHX'):
            raise ValueError('Invalid, overlapping or discontinuous mouth cue')
        previous = end
    if abs(previous - duration) > 0.025:
        raise ValueError('Cue timeline does not cover the WAV')
    return cues


def verify_engine(binary):
    spec = analyzer_profile()
    if not Path(binary).is_file() or digest(Path(binary)) != spec['binary_sha256']:
        raise ValueError('Unverified platform-specific Rhubarb executable; run explicit setup')
    return spec


def ensure_engine():
    spec = analyzer_profile()
    cache = ROOT / '.cache/lipsync'
    cache.mkdir(parents=True, exist_ok=True)
    binary = analyzer_path()
    archive = cache / ('rhubarb-windows.zip' if spec['format'] == 'zip' else 'rhubarb-npm.tgz')
    if not archive.is_file():
        partial = archive.with_suffix('.part')
        total = 0
        with urlopen(spec['url'], timeout=90) as source, partial.open('wb') as target:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                total += len(block)
                if total > 120 * 1024 * 1024:
                    raise ValueError('Analyzer archive exceeds setup budget')
                target.write(block)
        partial.replace(archive)
    if digest(archive) != spec['archive_sha256']:
        raise ValueError('Rhubarb platform archive checksum mismatch')
    base = binary.parent.resolve()

    def write(name, source):
        relative = archive_relative(name, spec)
        if relative is None:
            return
        target = (base / relative).resolve()
        if not target.is_relative_to(base):
            raise ValueError('Unsafe analyzer archive entry')
        content = source.read()
        if len(content) > 120 * 1024 * 1024:
            raise ValueError('Unexpected analyzer member size')
        if not target.is_file() or target.read_bytes() != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    # Always compare cached runtime files against the verified archive at setup.
    # No extractall, links, arbitrary DLLs or commands from archive metadata.
    if spec['format'] == 'zip':
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                relative = archive_relative(member.filename, spec)
                if member.is_dir() or relative is None:
                    continue
                if (member.external_attr >> 16) & 0o170000 == 0o120000 or member.file_size > 120 * 1024 * 1024:
                    raise ValueError('Unsafe analyzer ZIP member')
                with bundle.open(member) as source:
                    write(member.filename, source)
    else:
        with tarfile.open(archive) as bundle:
            for member in bundle:
                relative = archive_relative(member.name, spec)
                if member.isdir() or relative is None:
                    continue
                if not member.isfile() or member.size > 120 * 1024 * 1024:
                    raise ValueError('Unsafe analyzer archive member')
                with bundle.extractfile(member) as source:
                    write(member.name, source)
    verify_engine(binary)
    if spec['format'] != 'zip':
        binary.chmod(0o755)
    return binary


def analyze_wav(audio, dialog, destination, binary, runner=subprocess.run):
    """Analyze one actual WAV; no download, synthesis, guessed timing or fallback."""
    audio, dialog, destination = Path(audio), Path(dialog), Path(destination)
    spec = verify_engine(binary)
    metrics = audio_metadata(audio)
    runner([str(binary), '--threads', '2', '--machineReadable', '-f', 'json',
                    '-r', 'pocketSphinx', '-d', str(dialog), '-o', str(destination), str(audio)],
                   check=True, capture_output=True, text=True, timeout=90)
    data = json.loads(destination.read_text(encoding='utf-8'))
    validate_timeline(data, metrics['duration_seconds'])
    if digest(audio) != metrics['sha256']:
        raise ValueError('Audio changed during analysis')
    data['metadata']['soundFile'] = audio.name
    data['provenance'] = {
        'method': 'Rhubarb 1.13.0 PocketSphinx; dialog-guided estimated mouth classes',
        'audio_sha256': metrics['sha256'], 'dialog_sha256': digest(dialog),
        'binary_sha256': analyzer_profile()['binary_sha256'],
        'archive_sha256': analyzer_profile()['archive_sha256'],
        'archive_url': analyzer_profile()['url'], 'platform': analyzer_profile()['platform'],
        'hand_verified': False, 'phoneme_forced_alignment': False, 'espeak_timings_reused': False,
    }
    destination.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return data


def analyze(output):
    binary = ensure_engine()
    (output / 'cues').mkdir(parents=True, exist_ok=True)
    (output / 'proof').mkdir(parents=True, exist_ok=True)
    clips = []
    for filename, title, text, checks in REFERENCES:
        audio = output / 'audio' / filename
        metrics = audio_metadata(audio)
        stem = Path(filename).stem
        dialog = output / 'cues' / f'{stem}.txt'
        dialog.write_text(text.replace('’', "'") + '\n', encoding='utf-8')
        result = subprocess.run([str(binary), '--threads', '2', '--machineReadable', '-f', 'json',
                                 '-r', 'pocketSphinx', '-d', str(dialog), '-o',
                                 str(output / 'cues' / f'{stem}.json'), str(audio)],
                                check=True, capture_output=True, text=True, timeout=120)
        (output / 'proof' / f'{stem}-analysis.log').write_text(result.stderr)
        path = output / 'cues' / f'{stem}.json'
        data = json.loads(path.read_text())
        cues = validate_timeline(data, metrics['duration_seconds'])
        data['metadata']['soundFile'] = f'audio/{filename}'
        data['provenance'] = {
            'method': 'Rhubarb 1.13.0 PocketSphinx; dialog-guided estimated mouth classes',
            'audio_sha256': metrics['sha256'], 'dialog_sha256': digest(dialog),
            'binary_sha256': analyzer_profile()['binary_sha256'],
        'archive_sha256': analyzer_profile()['archive_sha256'],
        'archive_url': analyzer_profile()['url'], 'platform': analyzer_profile()['platform'],
            'hand_verified': False, 'phoneme_forced_alignment': False,
            'espeak_timings_reused': False,
        }
        path.write_text(json.dumps(data, indent=2) + '\n')
        clips.append({'file': f'audio/{filename}', 'title': title, 'text': text,
                      'duration': metrics['duration_seconds'], 'cues': cues, 'audio': metrics,
                      'analysis_file': f'cues/{stem}.json'})
    return clips


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/neural-head-demo')
    args = parser.parse_args()
    clips = analyze(args.output.resolve())
    print(json.dumps([{'file': clip['file'], 'cues': len(clip['cues']), 'duration': clip['duration']} for clip in clips], indent=2))
