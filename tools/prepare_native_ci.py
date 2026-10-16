"""Explicit online preparation using the corpus's EXACT prepared CC0 rig bytes.

PNG encoders may differ by platform. Never weaken the session identity check or
substitute an independently re-encoded model for the rig bound to a recording.
"""
import argparse
import hashlib
import json
from pathlib import Path
from build_neural_head import prepare_model
from build_native_head import build as native
from build_native_compare import build as compare
from build_neural_studio import build as presentation
from render_session import ROOT


def prepare(review):
    report=json.loads((review/'articulation.json').read_text());rigs=[s['rig'] for s in report['sessions']]
    if len(rigs)!=3 or any(r!=rigs[0] for r in rigs):raise ValueError('Expected three public recordings sharing one exact rig')
    expected=rigs[0]['model_sha256'];model=ROOT/'artifacts/neural-head-demo/model/mpfb-head.glb';reference=None
    if model.is_file():
        if model.stat().st_size>192*1024*1024:raise ValueError('Prepared reference rig exceeds budget')
        reference=model.read_bytes()
        if hashlib.sha256(reference).hexdigest()!=expected:raise ValueError('Staged prepared rig differs from corpus; download the exact public review artifact')
    # Fetch/check original pinned source and license provenance. This also builds
    # a local-platform derivative; restore the verified producer snapshot below.
    prepare_model()
    if reference is not None:model.write_bytes(reference)
    if hashlib.sha256(model.read_bytes()).hexdigest()!=expected:raise ValueError('Platform-prepared rig differs; stage the exact model from the public review artifact, not a re-encoded substitute')
    native(model,ROOT/'artifacts/native-head');presentation(prepare_speech=False);return compare(review)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,default=ROOT/'artifacts/neural-review');a=p.parse_args();prepare(a.review.resolve())
