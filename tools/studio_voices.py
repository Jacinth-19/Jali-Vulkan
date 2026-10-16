"""Explicitly installed stock voices from the checksum-pinned kokoro-js archive."""
from pathlib import Path
from prepare_kokoro_cpu import ASSETS, VOICE_SHA, archive, member, digest
import tarfile
VOICES={'af_heart':VOICE_SHA,'af_bella':'f69d836209b78eb8c66e75e3cda491e26ea838a3674257e9d4e5703cbaf55c8b','am_michael':'1d1f21dd8da39c30705cd4c75d039d265e9bc4a2a93ed09bc9e1b1225eb95ba1'}

def voice_file(name,directory=ASSETS):
    if name not in VOICES:raise ValueError('Unknown stock voice')
    path=Path(directory)/(name+'.bin')
    if not path.is_file() or path.stat().st_size!=522240 or digest(path)!=VOICES[name]:raise ValueError('Voice not installed/verified; explicitly run tools/studio_voices.py --install '+name)
    return path

def available(directory=ASSETS):
    result=[]
    for name in VOICES:
        try:voice_file(name,directory);result.append(name)
        except ValueError:pass
    return result

def install(name,directory=ASSETS):
    if name not in VOICES:raise ValueError('Unknown stock voice')
    with tarfile.open(archive('voice'),'r:gz') as bundle:
        with member(bundle,'package/voices/'+name+'.bin',600000) as source:data=source.read()
    import hashlib
    if hashlib.sha256(data).hexdigest()!=VOICES[name]:raise ValueError('Voice checksum mismatch')
    path=Path(directory)/(name+'.bin');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return path

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--install',choices=list(VOICES));a=p.parse_args()
    print(install(a.install) if a.install else available())
