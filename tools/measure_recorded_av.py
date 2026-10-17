"""Measure recorded flash/tone offsets from the local AV probe.

A synthetic fixture is NOT a physical laptop measurement. A camera recording
also contains camera AV sync, microphone/air-path and frame-quantization errors.
No recording or report uploads. Use a calibrated capture-device offset before
calling the result a corrected output-latency measurement; it is not lip contact.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import numpy as np


def edges(times,active):
    return [float(t) for i,(t,on) in enumerate(zip(times,active)) if on and (i==0 or not active[i-1])]


def summarize(audio,visual,*,physical=False,capture_offset_ms=None,capture_uncertainty_ms=None,frame_step_ms=33.34):
    if len(audio)<3 or len(visual)<3 or len(audio)!=len(visual) or len(audio)>20:raise ValueError('Need matching 3-20 recorded flash/tone events; do not silently drop markers')
    if any(not math.isfinite(v) or v<0 for v in [*audio,*visual]) or any(b<=a for events in (audio,visual) for a,b in zip(events,events[1:])):raise ValueError('Invalid recorded event times')
    raw=[(a-v)*1000 for a,v in zip(audio,visual)]
    if max(raw)-min(raw)>100:raise ValueError('Unstable/mismatched probe markers; review the recording')
    if not math.isfinite(frame_step_ms) or not 0<frame_step_ms<=100:raise ValueError('Unsupported recording frame interval')
    if (capture_offset_ms is None)!=(capture_uncertainty_ms is None):raise ValueError('Calibration requires offset AND uncertainty')
    if capture_offset_ms is not None and (not all(math.isfinite(v) for v in (capture_offset_ms,capture_uncertainty_ms)) or not 0<=capture_uncertainty_ms<=500 or abs(capture_offset_ms)>1000):raise ValueError('Invalid capture calibration')
    corrected=float(np.median(raw))-capture_offset_ms if capture_offset_ms is not None else None
    return {'schema':'jali-recorded-av-offset-v1','sign':'positive = recorded sound later than recorded flash','audio_onsets_seconds':audio,'visual_onsets_seconds':visual,'per_event_observed_offset_ms':raw,'median_observed_offset_ms':float(np.median(raw)),
            'capture_device_offset_ms':capture_offset_ms,'corrected_output_offset_ms':corrected,'minimum_timing_uncertainty_ms':frame_step_ms+10+(capture_uncertainty_ms or 0),
            'recording_claimed_physical_by_supplier':physical,'capture_calibration_independently_verified':False,'physical_av_accepted':False,'lip_sync_or_mesh_contact_verified':False,
            'limits':'Observed camera-track flash/tone offset, not speech-gesture timing. Calibration/source declarations require review. Includes unknown capture-device AV sync and microphone/acoustic path delay unless independently corrected. Uncertainty is a lower bound, not a confidence interval. Synthetic/loopback fixtures cannot certify physical laptop latency.'}


def analyze(recording,roi,physical=False,capture_offset_ms=None,capture_uncertainty_ms=None):
    import imageio_ffmpeg
    recording=Path(recording)
    if recording.suffix.lower() not in ('.mp4','.mov','.webm') or recording.stat().st_size>128*1024*1024:raise ValueError('Use a local MP4/MOV/WebM <=128 MiB, <=30 s of probe recording')
    if len(roi)!=4 or any(type(v)is not int or v<0 or v>8192 for v in roi) or min(roi[2:])<8:raise ValueError('ROI must be x y width height, at least 8x8')
    ff=imageio_ffmpeg.get_ffmpeg_exe();base=[ff,'-hide_banner','-copyts','-start_at_zero','-protocol_whitelist','file,pipe','-i',str(recording.resolve()),'-t','30']
    video=subprocess.run([*base,'-an','-vf',f'crop={roi[2]}:{roi[3]}:{roi[0]}:{roi[1]},scale=1:1:flags=area,format=gray,showinfo','-fps_mode','passthrough','-f','rawvideo','pipe:1'],capture_output=True,timeout=60,check=True)
    times=[float(t) for t in re.findall(r'pts_time:([\d.]+)',video.stderr.decode(errors='replace'))]
    pixels=np.frombuffer(video.stdout,dtype=np.uint8).astype(float)
    if len(times)!=len(pixels) or not 30<=len(times)<=3600:raise ValueError('Unexpected/bounded recording frame timeline')
    baseline=float(np.percentile(pixels,20));peak=float(np.percentile(pixels,99))
    if peak-baseline<60:raise ValueError('ROI lacks a clear dark-to-white probe marker')
    visual=edges(times,pixels>baseline+.6*(peak-baseline))
    decoded=subprocess.run([*base,'-vn','-af','aresample=48000,aformat=sample_fmts=flt:channel_layouts=mono,ashowinfo','-ac','1','-ar','48000','-f','f32le','pipe:1'],capture_output=True,timeout=60,check=True)
    timeline=[(float(t),int(n)) for t,n in re.findall(r'pts_time:([\d.]+).*?nb_samples:(\d+)',decoded.stderr.decode(errors='replace'))]
    if not timeline or any(abs(b[0]-(a[0]+a[1]/48000))>.0001 for a,b in zip(timeline,timeline[1:])):raise ValueError('Missing/discontinuous audio presentation timeline')
    pcm=np.frombuffer(decoded.stdout,dtype='<f4');N=480
    if len(pcm)>48000*30+N or not np.isfinite(pcm).all():raise ValueError('Invalid/bounded decoded audio')
    frames=pcm[:len(pcm)//N*N].reshape(-1,N);phase=np.arange(N)*2*np.pi*1200/48000
    energy=np.sum(frames*frames,axis=1);ratio=2*((frames@np.cos(phase))**2+(frames@np.sin(phase))**2)/(N*np.maximum(energy,1e-12))
    audio=edges(timeline[0][0]+np.arange(len(frames))*.01,(ratio>.45)&(energy/N>.00001))
    gaps=np.diff(times)
    result=summarize(audio,visual,physical=physical,capture_offset_ms=capture_offset_ms,capture_uncertainty_ms=capture_uncertainty_ms,frame_step_ms=float(max(gaps)*1000))
    result.update(recording_sha256=hashlib.sha256(recording.read_bytes()).hexdigest(),roi_pixels=roi,recording_processed_seconds=min(30,len(pcm)/48000),audio_detector='1200 Hz energy ratio >0.45 in 10 ms frames',video_detector='ROI luminance rise, actual decoded presentation timestamps')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recording',type=Path,required=True);p.add_argument('--roi',type=int,nargs=4,required=True);p.add_argument('--physical-recording',action='store_true');p.add_argument('--capture-offset-ms',type=float);p.add_argument('--capture-uncertainty-ms',type=float);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve()==a.recording.resolve():raise ValueError('Output must not overwrite the recording')
    result=analyze(a.recording,a.roi,a.physical_recording,a.capture_offset_ms,a.capture_uncertainty_ms);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
