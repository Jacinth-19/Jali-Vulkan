#!/usr/bin/env python3
"""Explicit pinned NONCOMMERCIAL sample setup; never called by runtime or EXE builds."""
import argparse
import hashlib
from pathlib import Path
import subprocess
from build_neural_head import github_file,SOURCE_COMMIT

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA='8864c504b5c11daa2f0037afffdc0815bb0fa2e6062e37a584746116a3c2f538'

def prepare(output,acknowledge):
    if not acknowledge:raise ValueError('Explicit --personal-noncommercial acknowledgement required. Read docs/eyes-hair-characters.md first.')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    readme=github_file(f'repos/met4citizen/TalkingHead/contents/README.md?ref={SOURCE_COMMIT}')
    if b'brunette.glb' not in readme or b'CC BY-NC 4.0' not in readme:raise ValueError('Pinned attribution statement missing')
    cache=ROOT/'.cache/character-samples';cache.mkdir(parents=True,exist_ok=True);source=cache/'brunette.glb'
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=SOURCE_SHA:
        data=github_file(f'repos/met4citizen/TalkingHead/contents/avatars/brunette.glb?ref={SOURCE_COMMIT}')
        if len(data)>5*1024*1024 or hashlib.sha256(data).hexdigest()!=SOURCE_SHA:raise ValueError('Sample identity mismatch')
        source.write_bytes(data)
    subprocess.run(['node','tools/prepare_character_sample.mjs',str(source),str(output)],cwd=ROOT,check=True,timeout=120)
    (output/'SOURCE-README.md').write_bytes(readme)
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--personal-noncommercial',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'artifacts/brunette-character');a=p.parse_args();print(prepare(a.output,a.personal_noncommercial))
