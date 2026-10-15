#!/usr/bin/env python3
"""Exercise the complete persistent PCM/phoneme/import/skin/raster worker protocol."""
import argparse
import json
from pathlib import Path
import select
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    process=subprocess.Popen([str(args.binary.resolve()),'--size','96','--text','Mama sees you.','--output',str(args.output.resolve())],
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        if not select.select([process.stdout],[],[],20)[0]:
            raise TimeoutError('Native startup timed out')
        line=process.stdout.readline(16384)
        if not line:
            raise RuntimeError(process.stderr.read().decode(errors='replace'))
        meta=json.loads(line)
        # Choose a different pose from the actual timing events, not guessed syllable times.
        cues=json.loads((args.output/'phonemes.json').read_text())
        vowel=next(c for c in cues if c['seconds']>0 and not c['symbol'].startswith('_') and c['symbol'] not in ('m','p','b'))
        command=f"0\n{vowel['seconds']:.9f}\nquit\n".encode()
        pixels,errors=process.communicate(command,timeout=20)
    except Exception:
        process.kill();process.communicate();raise
    if process.returncode:
        raise RuntimeError(errors.decode(errors='replace'))
    frame_size=96*96*4
    if meta['mode']!='live-mesh' or meta['alignment']!='tts-phoneme-events' or meta['morph_targets']!=3 or len(pixels)!=frame_size*2:
        raise RuntimeError('Invalid live metadata or frame protocol size')
    if pixels[:frame_size]==pixels[frame_size:]:
        raise RuntimeError('Phoneme-aligned frame poses did not change the rasterized image')
    if any(value!=255 for value in pixels[3::4]):
        raise RuntimeError('Invalid alpha in native raster frames')
    print(f"Live protocol passed: {meta['vertices']} imported vertices, {meta['phoneme_count']} phonemes, two distinct native frames, {meta['device']}")


if __name__=='__main__':
    main()
