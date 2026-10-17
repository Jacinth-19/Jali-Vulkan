"""Compare exact-WAV estimated cues against externally supplied phone annotations.

Never generates its own reference or turns a declaration into verified ground
truth. Mesh contact and perceptual/physical AV approval are separate checks.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from neural_session import validate_binding

PHONE_CLASS={'P':'A','B':'A','M':'A','F':'G','V':'G','L':'H','W':'F','UW':'F','AA':'D','SIL':'X'}


def compare(reference,clip):
    if reference.get('schema')!='jali-independent-phone-reference-v1' or reference.get('audio_sha256')!=clip['audio']['sha256'] or reference.get('text_sha256')!=clip['text_sha256']:raise ValueError('Reference must bind the exact WAV and transcript')
    provenance=reference.get('provenance',{})
    if provenance.get('kind') not in ('manual-phonetic-annotation','external-aligner'):raise ValueError('Explicit reference method required')
    for key in ('tool','annotator_or_model','method','source'):
        if not isinstance(provenance.get(key),str) or not 1<=len(provenance[key])<=500:raise ValueError('Missing bounded reference provenance: '+key)
    related=' '.join(str(v) for v in provenance.values()).lower()
    if any(s in related for s in ('rhubarb','pocketsphinx','pocket sphinx','cmusphinx','cmu sphinx')):raise ValueError('Related Sphinx reference cannot satisfy independent-reference intake')
    if provenance.get('kind')=='external-aligner' and not re.fullmatch('[0-9a-f]{64}',str(provenance.get('model_sha256',''))):raise ValueError('External aligner must identify its acoustic model hash')
    events=reference.get('phones');previous=0;rows=[]
    if not isinstance(events,list) or not 1<=len(events)<=2000:raise ValueError('Reference needs 1-2000 explicit phones')
    for event in events:
        a,b,u=(event.get(k) for k in ('start','end','uncertainty_ms'))
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (a,b,u)) or not 0<=previous<=a<b<=clip['duration'] or not 0<=u<=250:raise ValueError('Invalid/overlapping reference phone or uncertainty')
        previous=b;phone=event.get('phone');label=PHONE_CLASS.get(phone)
        if label is None:continue  # No invented viseme for unsupported phones.
        candidates=[c for c in clip['cues'] if c['value']==label and c['end']>a-.25 and c['start']<b+.25]
        overlaps=[max(0,min(b,c['end'])-max(a,c['start'])) for c in candidates]
        chosen=max(zip(overlaps,candidates),key=lambda p:p[0],default=(0,None))[1]
        rows.append({'phone':phone,'reference_start':a,'reference_end':b,'reference_uncertainty_ms':u,'estimated_class':label,'estimated_class_coverage':min(1,sum(overlaps)/(b-a)),
                     'nearest_estimated_start_error_ms':(chosen['start']-a)*1000 if chosen else None,'missing_estimated_gesture':chosen is None,'contact_verified':False})
    if not rows:raise ValueError('No supported diagnostic phone classes in reference')
    return {'schema':'jali-independent-reference-comparison-v1','audio_sha256':clip['audio']['sha256'],'text_sha256':clip['text_sha256'],'provenance':provenance,'rows':rows,
            'independence_declared_by_supplier':True,'provenance_independently_audited':False,'human_quality_accepted':False,'mesh_contact_verified':False,'physical_av_measured':False,'automatic_tuning_applied':False,
            'limits':'External annotations supplied by the user, not generated from the tested cues. Intake checks hashes, method and bounds, not truth of provenance. Acoustic phone intervals and visible gestures need not share boundaries. Errors are diagnostics, not automatic offset/gain prescriptions.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--reference',type=Path);group.add_argument('--make-template',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve() in [a.manifest.resolve(),*((a.manifest.parent/f).resolve() for f in ('audio.wav','cues.json','requested-text.txt')),*( [a.reference.resolve()] if a.reference else [])]:raise ValueError('Output must not overwrite source media, manifest or reference')
    if a.make_template:
        clip=json.loads(a.manifest.read_text());template={'schema':'jali-independent-phone-reference-v1','audio_sha256':clip['audio']['sha256'],'text_sha256':clip['text_sha256'],'provenance':{'kind':'manual-phonetic-annotation','tool':'','annotator_or_model':'','method':'','source':''},'phones':[],'instructions':'Annotate this exact WAV independently. Add phone/start/end/uncertainty_ms. Do not copy Rhubarb/PocketSphinx cues into the reference.'};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(template,indent=2)+'\n');return
    if a.reference.stat().st_size>512*1024:raise ValueError('Reference exceeds 512 KiB')
    clip=json.loads(a.manifest.read_text());root=a.manifest.parent
    validate_binding(clip,root/'audio.wav',json.loads((root/'cues.json').read_text()),clip['rig'])
    result=compare(json.loads(a.reference.read_text()),clip);result['reference_sha256']=hashlib.sha256(a.reference.read_bytes()).hexdigest();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
