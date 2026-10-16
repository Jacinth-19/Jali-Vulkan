#!/usr/bin/env python3
"""Bounded local stock neural TTS CLI (M1), also used by the connected M2 worker.

Setup explicitly with prepare_kokoro_cpu.py; synthesis has no download or API
fallback. The tested q8 export differs from kokoro-onnx's default export: its
speed input is float32 and waveform is [1,N]. Adapt those types explicitly.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import wave

from prepare_kokoro_cpu import ASSETS, MODEL_SHA, VOICE_SHA, digest


DEFAULT_TEXTS = [
    'Hello. This new sentence was generated locally on the CPU. Next, we will use this recording and its text to animate our character.',
    'Please pack the blue paper bag. My little robot can now make a new voice recording without calling a paid speech service.',
]


def validate_request(text, speed=1.0, threads=2):
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError('Text must contain 1-500 characters with some non-whitespace content')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
        raise ValueError('Text contains unsupported control characters')
    if isinstance(speed, bool) or not isinstance(speed, (float, int)) or not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
        raise ValueError('Speed must be finite and between 0.5 and 2.0')
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 8:
        raise ValueError('Threads must be an integer between 1 and 8')


def verify_assets(directory):
    for name, expected in [('model_quantized.onnx', MODEL_SHA), ('af_heart.bin', VOICE_SHA)]:
        path = directory / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'Missing or mismatched {name}; explicitly run prepare_kokoro_cpu.py')


def peak_rss_mib():
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(value / (1024 * 1024 if sys.platform == 'darwin' else 1024), 2)
    except ImportError:
        return None  # Windows measurement remains a target-device task.


def write_audio(path, audio, rate):
    import numpy as np
    if audio.ndim != 1 or rate != 24000 or not rate / 10 <= audio.size <= rate * 60 or not np.isfinite(audio).all():
        raise ValueError('Invalid or out-of-budget neural waveform')
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    if peak < 0.001 or rms <= 0:
        raise ValueError('Neural output is silent')
    clipped = float(np.mean(np.abs(audio) > 1))
    pcm = np.round(np.clip(audio, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    return {'sample_rate': rate, 'channels': 1, 'sample_width_bits': 16,
            'duration_seconds': audio.size / rate, 'peak_amplitude_before_pcm': peak,
            'rms_dbfs': round(20 * math.log10(rms), 2), 'clipped_sample_fraction': clipped,
            'sha256': digest(path)}


def run(texts, output, directory=ASSETS, speed=1.0, threads=2):
    for text in texts:
        validate_request(text, speed, threads)
    verify_assets(directory)  # Fail before importing/executing the model runtime.
    output.mkdir(parents=True, exist_ok=True)
    (output / 'manifest.json').unlink(missing_ok=True)
    start = time.perf_counter()
    import numpy as np
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    import_seconds = time.perf_counter() - start
    ort.disable_telemetry_events()
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    start = time.perf_counter()
    session = ort.InferenceSession(str(directory / 'model_quantized.onnx'), sess_options=options,
                                   providers=['CPUExecutionProvider'])
    if session.get_providers() != ['CPUExecutionProvider']:
        raise ValueError('CPU-only provider requirement failed')
    schema = {i.name: i.type for i in session.get_inputs()}
    if schema != {'input_ids': 'tensor(int64)', 'style': 'tensor(float)', 'speed': 'tensor(float)'}:
        raise ValueError(f'Unexpected model inputs: {schema}')
    styles = np.fromfile(directory / 'af_heart.bin', dtype='<f4').reshape(510, 1, 256)
    if not np.isfinite(styles).all():
        raise ValueError('Invalid stock voice data')

    class ExportAdapter(Kokoro):
        def _create_audio(self, phonemes, voice, speed):
            tokens = self.tokenizer.tokenize(phonemes)
            if not 0 < len(tokens) < len(voice):
                raise ValueError('Phoneme sequence exceeds the stock style-table budget; shorten text')
            inputs = {'input_ids': np.array([[0, *tokens, 0]], dtype=np.int64),
                      'style': np.asarray(voice[len(tokens)], dtype=np.float32),
                      'speed': np.array([speed], dtype=np.float32)}
            waveform = self.sess.run(['waveform'], inputs)[0]
            if waveform.ndim != 2 or waveform.shape[0] != 1:
                raise ValueError('Unexpected model waveform shape')
            return waveform[0], 24000

    # np.load defaults to no pickle. This temporary NPZ is made only from the
    # checksum-verified, finite raw float voice tensor, not a downloaded pickle.
    with tempfile.TemporaryDirectory(prefix='jali-kokoro-') as temp:
        voices = Path(temp) / 'voices.npz'
        np.savez(voices, af_heart=styles)
        engine = ExportAdapter.from_session(session, str(voices))
        # Close the lazy NPZ reader before Windows tries to remove the temp file.
        engine.voices.close()
        engine.voices = {'af_heart': styles}
        load_seconds = time.perf_counter() - start
        clips = []
        for index, text in enumerate(texts):
            start = time.perf_counter()
            samples, rate = engine.create(text, voice='af_heart', speed=speed, lang='en-us')
            generation_seconds = time.perf_counter() - start
            filename = f'{index + 1:02d}-local-neural.wav'
            metrics = write_audio(output / filename, samples, rate)
            (output / f'{index + 1:02d}-requested-text.txt').write_text(text + '\n', encoding='utf-8')
            clips.append({'file': filename, 'requested_text': text,
                          'transcript_independently_verified': False,
                          'phoneme_timestamps': None,
                          'generation_seconds': round(generation_seconds, 4),
                          'real_time_factor': round(generation_seconds / metrics['duration_seconds'], 4),
                          **metrics})
            print(f"{filename}: {metrics['duration_seconds']:.2f}s audio in {generation_seconds:.2f}s (RTF {clips[-1]['real_time_factor']})", flush=True)
    report = {
        'schema': 1, 'method': 'Local neural Kokoro-82M v1.0 q8 / ONNX Runtime CPU',
        'stock_voice': 'af_heart', 'same_as_previous_arena_voice_00': False,
        'cloned_identity': False, 'remote_speech_api_used': False,
        'audio_backend': 'Neural ONNX waveform; eSpeak NG is used only for text phonemization',
        'phonemizer_note': 'Different G2P frontends may affect pronunciation. Text+audio alone are not timed phoneme alignment.',
        'platform': platform.platform(), 'python': platform.python_version(),
        'host_logical_cpus': os.cpu_count(), 'cpu_threads': threads,
        'providers': session.get_providers(), 'speed': speed,
        'dependency_import_seconds': round(import_seconds, 4), 'engine_load_seconds': round(load_seconds, 4),
        'process_peak_rss_mib': peak_rss_mib(),
        'memory_scope': 'Linux/macOS process high-water RSS including dependencies/model; not system RAM, not isolated model size',
        'model_sha256': MODEL_SHA, 'voice_sha256': VOICE_SHA,
        'packages': {name: importlib.metadata.version(name) for name in
                     ('kokoro-onnx', 'onnxruntime', 'numpy', 'phonemizer-fork', 'espeakng-loader')},
        'clips': clips,
        'limitations': ['This standalone CLI is audio-only; use neural_studio_server.py for connected face playback.',
                        'Windows target laptop has not been tested.',
                        'No human intelligibility/naturalness review is claimed by numerical waveform checks.',
                        'No phoneme timing is returned by this waveform-only export.',
                        '500-character request cap; oversized/invalid results fail, not silently truncated by this adapter.'],
    }
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('providers', 'engine_load_seconds', 'process_peak_rss_mib')}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', help='One new sentence; omitted runs two new regression sentences')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'artifacts/local-neural-speech')
    parser.add_argument('--models', type=Path, default=ASSETS)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--speed', type=float, default=1.0)
    args = parser.parse_args()
    try:
        run([args.text] if args.text is not None else DEFAULT_TEXTS, args.output.resolve(), args.models.resolve(), args.speed, args.threads)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
