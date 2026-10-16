#!/usr/bin/env python3
"""Render the SAME verified neural WAV/cue session through actual native Vulkan."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image
from neural_session import validate_binding
from neural_visemes import shared_shapes,sample
from rich_worker import RichWorker
from render_session import ROOT
from audit_native_rig import read_glb


def validate_session(manifest,asset):
    clip=json.loads(manifest.read_text(encoding='utf-8'));cues=json.loads((manifest.parent/'cues.json').read_text(encoding='utf-8'))
    validate_binding(clip,manifest.parent/'audio.wav',cues,clip['rig'])
    source=read_glb(asset)['extras']['source_sha256']
    if source!=clip['rig']['model_sha256']:raise ValueError('Native asset and WebGL session source differ')
    if hashlib.sha256((ROOT/'web/neural-head/visemes.mjs').read_bytes()).hexdigest()!=clip['rig']['retarget_sha256']:raise ValueError('Session retarget version differs from native adapter')
    return clip


def render(manifest,asset,output,software=False,fps=12,video=True):
    if not 1<=fps<=30:raise ValueError('FPS must be 1-30')
    clip=validate_session(manifest,asset);shapes=shared_shapes();output.mkdir(parents=True,exist_ok=True)
    worker=RichWorker(asset,output,software,test=True);frames=[]
    try:
        # Actual class-center PNGs, not hand-authored pose replacements.
        for value in ('A','D','F','G','H'):
            found=[c for c in clip['cues'] if c['value']==value]
            if not found:continue
            cue=max(found,key=lambda c:c['end']-c['start']);t=(cue['start']+cue['end'])/2
            weights=sample(clip,t,shapes);rgba,ms=worker.frame(weights);path=output/f'pose-{value}.png'
            Image.frombytes('RGBA',(512,512),rgba).save(path)
            frames.append({'file':path.name,'time':t,'estimated_class':value,'weights':weights,'readback_ms':ms,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        if video:
            import imageio_ffmpeg
            with tempfile.TemporaryDirectory(prefix='jali-native-frames-') as temp:
                for i in range(math.ceil(clip['duration']*fps)):
                    rgba,_=worker.frame(sample(clip,i/fps,shapes));Image.frombytes('RGBA',(512,512),rgba).convert('RGB').save(Path(temp)/f'frame-{i:05}.jpg',quality=93)
                subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate',str(fps),'-i',str(Path(temp)/'frame-%05d.jpg'),'-i',str(manifest.parent/'audio.wav'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',str(output/'performance.mp4')],check=True,timeout=120)
        evidence={'schema':'jali-native-neural-session-v1','session_id':clip['id'],'text':clip['text'],'audio_sha256':clip['audio']['sha256'],'native_asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'source_rig':clip['rig'],'renderer':worker.metadata,'frames':frames,'fps':fps if video else None,'limits':'Actual software/hardware device flag recorded; offline video is not live FPS, independent articulation review or physical AV validation.'}
        (output/'session-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');return evidence
    finally:worker.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--asset',type=Path,default=ROOT/'artifacts/native-head/mpfb-native.glb');p.add_argument('--output',type=Path,default=ROOT/'artifacts/native-head-proof');p.add_argument('--software-vulkan',action='store_true');p.add_argument('--no-video',action='store_true');a=p.parse_args();render(a.manifest.resolve(),a.asset.resolve(),a.output.resolve(),a.software_vulkan,video=not a.no_video)
