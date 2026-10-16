"""Optional native presentation of the studio's same immutable WAV/cue sessions."""
import io
import math
import os
from pathlib import Path
import sys
from audit_native_rig import read_glb
from neural_visemes import shared_shapes,sample
from rich_worker import RichWorker
from render_session import ROOT


def performance(weights,time,duration,life,mood,gaze):
    pose=dict(weights);active=life and 0<time<duration
    protected=min(1,max(weights.get('viseme_PP',0)/.95,weights.get('viseme_FF',0)/.85,weights.get('viseme_U',0)/.88,weights.get('viseme_O',0)/.65))
    if mood=='warm':pose.update(mouthSmileLeft=.16*(1-protected),mouthSmileRight=.16*(1-protected),cheekSquintLeft=.06*(1-protected),cheekSquintRight=.06*(1-protected))
    if mood=='attentive':pose.update(browInnerUp=.25,browOuterUpLeft=.12,browOuterUpRight=.12)
    if active:pose['eyeBlinkLeft']=pose['eyeBlinkRight']=max(0,1-abs((time+.7)%3.8-3.25)/.11)
    return pose,{'head_yaw':math.sin(time*.73)*.018 if active else 0,'head_roll':math.sin(time*.51)*.008 if active else 0,
        'eye_yaw':.08 if gaze=='left' else -.08 if gaze=='right' else 0,'eye_pitch':.06 if gaze=='down' else 0}


class NativeStudio:
    def __init__(self,asset,rig,software=False):
        source=read_glb(asset)['extras']['source_sha256']
        if source!=rig['model_sha256']:raise ValueError('Native profile and studio source rig differ')
        self.rig=rig;self.shapes=shared_shapes()
        output=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.jali')))/'JaliVulkan/native-engine'/str(os.getpid()) if getattr(sys,'frozen',False) else ROOT/'artifacts/native-studio'
        self.worker=RichWorker(asset,output,software)
        self.metadata={**self.worker.metadata,'source_model_sha256':source,'camera':'fixed native portrait camera; lighting differs from WebGL'}
    def frame(self,clip,query):
        if clip['rig']!=self.rig:raise ValueError('Native clip/rig identity mismatch')
        t=float(query['time'][0]);trim=float(query.get('trim',['0'])[0])/1000
        mood=query.get('mood',['neutral'])[0];gaze=query.get('gaze',['forward'])[0];life=query.get('life',['1'])[0];sync=query.get('sync',['1'])[0]
        if not math.isfinite(t) or not 0<=t<=clip['duration']+.25 or not math.isfinite(trim) or abs(trim)>.15 or mood not in ('neutral','warm','attentive') or gaze not in ('forward','left','right','down') or life not in ('0','1') or sync not in ('0','1'):raise ValueError('Invalid native clock or control')
        weights=sample(clip,t,self.shapes,trim,sync=='1')
        pose,motion=performance(weights,t,clip['duration'],life=='1',mood,gaze)
        from PIL import Image
        rgba,ms=self.worker.frame(pose,motion);encoded=io.BytesIO();Image.frombytes('RGBA',(512,512),rgba).convert('RGB').save(encoded,format='JPEG',quality=91)
        return encoded.getvalue(),ms
    def close(self):self.worker.close()
