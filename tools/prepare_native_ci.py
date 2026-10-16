"""Explicit online preparation for the public-corpus native comparison only."""
import argparse
from pathlib import Path
from build_neural_head import prepare_model
from build_native_head import build as native
from build_native_compare import build as compare
from build_neural_studio import build as presentation
from render_session import ROOT
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,default=ROOT/'artifacts/neural-review');a=p.parse_args()
    prepare_model();native(ROOT/'artifacts/neural-head-demo/model/mpfb-head.glb',ROOT/'artifacts/native-head');presentation(prepare_speech=False);compare(a.review.resolve())
