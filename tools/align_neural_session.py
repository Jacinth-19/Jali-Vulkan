#!/usr/bin/env python3
"""Optional phone-level forced-alignment CROSSCHECK, never human ground truth.

PocketSphinx is a separate two-pass aligner, but related to Rhubarb's acoustic
model family. Do not manufacture an 'independent reviewed reference' from this.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import subprocess
from neural_session import validate_binding
from render_session import ROOT


def normalized_words(text):
    text=text.lower().replace('’',"'")
    if re.search(r"[^a-z\s.,!?:;'\"()\-]",text):raise ValueError('Alignment needs English dictionary words; spell numbers explicitly')
    words=re.findall(r"[a-z]+(?:'[a-z]+)?",text)
    if not words:raise ValueError('No alignment words')
    return words


def phone_windows(words,duration,frame_rate=100):
    phones=[];previous=0
    for word in words:
        for phone in word['phones']:
            start=phone['start_frame']/frame_rate;end=(phone['start_frame']+phone['frames'])/frame_rate
            if not all(math.isfinite(v) for v in (start,end)) or not (0<=previous<=start<end<=duration+.02 and start<duration):raise ValueError('Invalid forced phone timeline')
            previous=end;name=phone['phone'];mouth='A' if name in ('P','B','M') else 'G' if name in ('F','V') else 'H' if name=='L' else 'X' if name=='SIL' else None
            phones.append({**phone,'word':word['word'],'start':start,'end':min(end,duration),'diagnostic_class':mouth})
    if not phones:raise ValueError('No aligned phones')
    return phones


def crosscheck(phones,clip):
    out=[]
    for phone in phones:
        label=phone['diagnostic_class']
        if label is None:continue
        start,end=phone['start'],phone['end'];cues=[c for c in clip['cues'] if c['value']==label and c['end']>start and c['start']<end]
        overlap=sum(max(0,min(end,c['end'])-max(start,c['start'])) for c in cues)
        out.append({'phone':phone['phone'],'word':phone['word'],'start':start,'end':end,'approximate_class':label,
            'estimated_class_coverage':min(1,overlap/(end-start)),'matching_estimated_cues':cues})
    return out


def align(clip,wav,binding,output):
    validate_binding(clip,wav,binding,clip['rig']);words=normalized_words(clip['text'])
    if importlib.metadata.version('pocketsphinx')!='5.0.4':raise ValueError('Explicitly install pocketsphinx==5.0.4 --no-deps')
    import imageio_ffmpeg
    from pocketsphinx import Decoder,get_model_path
    model=Path(get_model_path());decoder=Decoder(lm=None,loglevel='ERROR',samprate=16000)
    missing=sorted({w for w in words if not decoder.lookup_word(w)})
    if missing:raise ValueError('Out-of-dictionary words; no invented pronunciations or substitute timings: '+', '.join(missing))
    pcm=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-protocol_whitelist','file,pipe','-i',str(wav.resolve()),'-ac','1','-ar','16000','-f','s16le','pipe:1'],timeout=20)
    if len(pcm)>16000*2*60 or abs(len(pcm)/(16000*2)-clip['duration'])>.002:raise ValueError('Alignment resample duration/budget')
    decoder.set_align_text(' '.join(words))
    for second_pass in (False,True):
        if second_pass:decoder.set_alignment()
        decoder.start_utt();decoder.process_raw(pcm,full_utt=True);decoder.end_utt()
    aligned=[{'word':w.name,'start_frame':w.start,'frames':w.duration,'phones':[{'phone':p.name,'start_frame':p.start,'frames':p.duration,'raw_log_score':p.score} for p in w]} for w in decoder.get_alignment()]
    observed=[re.sub(r'\(\d+\)$','',w['word']) for w in aligned if w['word'] not in ('<s>','</s>','<sil>')]
    if observed!=words:raise ValueError('Forced alignment did not preserve the full requested word sequence')
    phones=phone_windows(aligned,clip['duration']);output.mkdir(parents=True,exist_ok=True)
    distribution=importlib.metadata.distribution('pocketsphinx');licenses=output/'licenses';licenses.mkdir(exist_ok=True)
    for f in distribution.files:
        if str(f).endswith('/LICENSE'):(licenses/'PocketSphinx-5.0.4-LICENSE.txt').write_bytes(distribution.locate_file(f).read_bytes())
    (licenses/'acoustic-model-README.txt').write_bytes((model/'en-us/en-us/README').read_bytes())
    files=[model/'en-us/cmudict-en-us.dict']+sorted(p for p in (model/'en-us/en-us').iterdir() if p.is_file())
    result={'schema':'jali-phone-alignment-crosscheck-v1','audio_sha256':clip['audio']['sha256'],'text_sha256':clip['text_sha256'],
        'method':'PocketSphinx 5.0.4 two-pass transcript-constrained word and phone alignment, 16 kHz resample, 100 frames/sec',
        'normalized_transcript':' '.join(words),'alignment_pcm_sha256':hashlib.sha256(pcm).hexdigest(),
        'model_files':{str(p.relative_to(model)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'frame_rate':100,'words':aligned,'phones':phones,'critical_phone_crosscheck':crosscheck(phones,clip),
        'independent_of_rhubarb':False,'human_review_completed':False,'quality_score':None,
        'limits':'Separate forced-alignment implementation, related Sphinx acoustic family. Not independent ground truth, calibrated confidence, actual lip contact or a physical AV measurement. Acoustic phone intervals are not necessarily visual gesture boundaries; no automatic rig/timing tuning is applied.'}
    (output/'alignment.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--manifest',type=Path);group.add_argument('--review',type=Path);p.add_argument('--wav',type=Path);p.add_argument('--cues',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.review:
        report=json.loads((a.review/'articulation.json').read_text());corpus=json.loads((ROOT/'tests/fixtures/neural-articulation.json').read_text())
        if [c['text'] for c in report['sessions']]!=[c['text'] for c in corpus['cases']]:raise ValueError('Only the fixed public corpus may be batch-exported')
        for case,clip in zip(corpus['cases'],report['sessions']):
            binding=json.loads((a.review/'sessions'/f"{case['id']}-cues.json").read_text());r=align(clip,a.review/'sessions'/f"{case['id']}-audio.wav",binding,a.output/case['id']);print(case['id'],len(r['phones']),'aligned phones; human review still pending')
    else:
        clip=json.loads(a.manifest.read_text());wav=a.wav or a.manifest.parent/'audio.wav';binding=json.loads((a.cues or a.manifest.parent/'cues.json').read_text());align(clip,wav,binding,a.output)


if __name__=='__main__':main()
