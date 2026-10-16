#!/usr/bin/env python3
"""M2: new local speech -> analyze that WAV with its text -> immutable face session."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from analyze_neural_clips import analyze_wav, audio_metadata, digest, validate_timeline
from local_neural_speech import validate_request
from prepare_kokoro_cpu import MODEL_SHA, VOICE_SHA

ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = re.compile(r'[a-f0-9]{32}\Z')
MEDIA = {'audio.wav', 'cues.json', 'requested-text.txt', 'manifest.json'}


def text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_binding(clip, wav, cue_data, rig):
    """Fail closed if a session uses another waveform, text, cue set or rig."""
    actual = audio_metadata(wav)
    if clip['audio']['sha256'] != actual['sha256'] or cue_data['provenance']['audio_sha256'] != actual['sha256']:
        raise ValueError('Audio/cue session hash mismatch')
    if clip['text_sha256'] != text_hash(clip['text']) or clip['rig'] != rig:
        raise ValueError('Text or rig session mismatch')
    if abs(clip['duration'] - actual['duration_seconds']) > 0.0001:
        raise ValueError('Audio duration mismatch')
    validate_timeline(cue_data, actual['duration_seconds'])
    if clip['cues'] != cue_data['mouthCues']:
        raise ValueError('Published cues differ from the analyzed waveform')
    if not SESSION_ID.fullmatch(clip['id']) or clip['file'] != f"/sessions/{clip['id']}/audio.wav":
        raise ValueError('Invalid session identity')


def build_session(session_id, text, directory, rig, rhubarb, on_stage=lambda _: None):
    token = getattr(on_stage, 'cancel_token', None)
    runner = token.run if token else subprocess.run
    if token: token.check()
    validate_request(text)
    if not SESSION_ID.fullmatch(session_id):
        raise ValueError('Invalid session ID')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    on_stage('synthesizing')
    # Isolate the neural runtime and bound each request. No shell, user commands,
    # model URLs, uploaded conditioning, or cached speech from another session.
    result = runner([sys.executable, str(ROOT / 'tools/local_neural_speech.py'),
                             '--text', text, '--output', str(directory / 'speech'), '--threads', '2'],
                            cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf-8', timeout=90)
    (directory / 'worker.log').write_text((result.stdout + result.stderr)[-32000:], encoding='utf-8')
    speech = json.loads((directory / 'speech/manifest.json').read_text())
    if (speech['providers'] != ['CPUExecutionProvider'] or speech['remote_speech_api_used'] is not False
            or speech['model_sha256'] != MODEL_SHA or speech['voice_sha256'] != VOICE_SHA
            or len(speech['clips']) != 1 or speech['clips'][0]['requested_text'] != text):
        raise ValueError('Unverified local speech result')
    wav = directory / 'audio.wav'
    shutil.copy2(directory / 'speech/01-local-neural.wav', wav)
    metrics = audio_metadata(wav)
    if metrics['sha256'] != speech['clips'][0]['sha256']:
        raise ValueError('Synthesized waveform changed')
    (directory / 'requested-text.txt').write_text(text, encoding='utf-8')
    dialog = directory / 'dialog.txt'
    dialog.write_text(text.replace('’', "'") + '\n', encoding='utf-8')
    on_stage('analyzing')
    analysis_start = time.perf_counter()
    cues = analyze_wav(wav, dialog, directory / 'cues.json', rhubarb, runner=runner)
    clip = {
        'id': session_id, 'title': 'Local neural performance', 'text': text,
        'text_sha256': text_hash(text), 'file': f'/sessions/{session_id}/audio.wav',
        'duration': metrics['duration_seconds'], 'cues': cues['mouthCues'], 'audio': metrics,
        'rig': rig, 'tts': {key: speech[key] for key in
                           ('method', 'stock_voice', 'providers', 'model_sha256', 'voice_sha256',
                            'engine_load_seconds', 'dependency_import_seconds', 'process_peak_rss_mib', 'memory_scope', 'platform', 'python')},
        'generation_seconds': speech['clips'][0]['generation_seconds'],
        'analysis_seconds': round(time.perf_counter() - analysis_start, 4),
        'analysis': cues['provenance'], 'total_seconds': round(time.perf_counter() - start, 4),
        'transcript_independently_verified': False,
        'limits': 'Estimated nine-class visemes, not verified phoneme alignment; procedural/manual expression; WebGL, not native Vulkan.',
    }
    validate_binding(clip, wav, cues, rig)
    if cues['provenance']['dialog_sha256'] != digest(dialog):
        raise ValueError('Dialog changed during analysis')
    if token: token.check()
    target = directory / 'manifest.json'
    temporary = directory / 'manifest.part'
    temporary.write_text(json.dumps(clip, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(target)
    return clip
