"""Inventory installed distribution notices without claiming legal clearance."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
from prepare_kokoro_cpu import MODEL_SHA
from studio_voices import VOICES,available

def inventory():
    names=('kokoro-onnx','onnxruntime','numpy','phonemizer-fork','espeakng-loader','Pillow','imageio-ffmpeg','pyinstaller')
    packages=[]
    for name in names:
        try:
            d=metadata.distribution(name);m=d.metadata
            packages.append({'name':name,'version':d.version,'declared_license':m.get('License-Expression') or m.get('License'),'project_urls':m.get_all('Project-URL') or [],'notice_files':[str(f) for f in d.files or [] if any(s in str(f).lower() for s in ('license','copying','notice'))]})
        except metadata.PackageNotFoundError:packages.append({'name':name,'installed':False})
    return {'schema':'jali-release-inventory-v1','packages':packages,'model_sha256':MODEL_SHA,'installed_stock_voices':{v:VOICES[v] for v in available()},'public_redistribution_approved':False,'signing_required_for_personal_use':False,'limits':'Metadata/notice discovery is not corresponding source, provenance verification or legal approval. See docs/release-gates.json.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(inventory(),indent=2)+'\n')
