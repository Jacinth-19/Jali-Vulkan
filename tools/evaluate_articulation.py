"""Compare manually/independently marked reference windows with estimated cues.

Never manufactures references from Rhubarb. Reviewer/source independence is a
user declaration, not cryptographically or perceptually verified by this tool.
"""
import argparse
import hashlib
import json
import math

from analyze_neural_clips import validate_timeline, audio_metadata
from pathlib import Path


def evaluate(reference, clip):
    validate_timeline({'metadata':{'duration':clip['duration']},'mouthCues':clip['cues']},clip['duration'])
    if hashlib.sha256(clip['text'].encode('utf-8')).hexdigest()!=clip['text_sha256']:
        raise ValueError('Clip text hash mismatch')
    if reference.get('audio_sha256')!=clip['audio']['sha256']:
        raise ValueError('Reference belongs to a different waveform')
    if reference.get('text_sha256')!=clip['text_sha256']:
        raise ValueError('Reference text does not match')
    if (reference.get('method') not in ('manual-listening-waveform','independent-aligner') or
        reference.get('independent_of_rhubarb') is not True or not isinstance(reference.get('reviewer'),str) or
        not reference['reviewer'].strip() or not isinstance(reference.get('source'),str) or not reference['source'].strip()):
        raise ValueError('An explicitly attributed independent reference is required')
    events=reference.get('events')
    if not isinstance(events,list) or not 1<=len(events)<=1000:
        raise ValueError('No reviewed reference events; pending templates are not evaluation')
    results=[];previous=0
    for e in events:
        start,end,tolerance=e.get('start'),e.get('end'),e.get('uncertainty_seconds')
        if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in (start,end,tolerance)):
            raise ValueError('Reference times and uncertainty must be finite numbers')
        if not 0<=previous<=start<end<=clip['duration'] or not 0<=tolerance<=.25 or e.get('class') not in list('ABCDEFGHX'):
            raise ValueError('Invalid/overlapping reference interval or class')
        previous=end
        candidates=[c for c in clip['cues'] if c['value']==e['class'] and c['end']>start and c['start']<end]
        overlap=sum(max(0,min(end,c['end'])-max(start,c['start'])) for c in candidates)
        best=max(candidates,key=lambda c:max(0,min(end,c['end'])-max(start,c['start'])),default=None)
        onset=best['start']-start if best else None;offset=best['end']-end if best else None
        results.append({'reference':e,'estimated_class_coverage':min(1,overlap/(end-start)),
            'best_overlapping_cue':best,'onset_error_seconds':onset,'offset_error_seconds':offset,
            'boundaries_within_declared_uncertainty':best is not None and abs(onset)<=tolerance and abs(offset)<=tolerance})
    return {'schema':'jali-reference-comparison-v1','audio_sha256':clip['audio']['sha256'],
        'reference_provenance':{k:reference[k] for k in ('method','reviewer','source','independent_of_rhubarb')},
        'reference_independence_verified_by_tool':False,'events':results,'quality_score':None,
        'limits':'Only supplied reference windows, not full-utterance accuracy, naturalness, lip contact, displayed frames or physical AV latency.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True,type=Path);parser.add_argument('--clip',required=True,type=Path)
    parser.add_argument('--wav',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    clip=json.loads(args.clip.read_text(encoding='utf-8'));actual=audio_metadata(args.wav)
    if actual['sha256']!=clip['audio']['sha256'] or abs(actual['duration_seconds']-clip['duration'])>1e-4:
        raise ValueError('Actual reference WAV does not match the clip')
    result=evaluate(json.loads(args.reference.read_text(encoding='utf-8')),clip)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
