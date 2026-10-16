"""Publish bounded public-corpus metrics as CI annotations; never private input."""
import json
import os
from pathlib import Path
import sys

from neural_platform import analyzer_profile
from prepare_kokoro_cpu import MODEL_SHA,VOICE_SHA

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.platform!='win32':
        raise ValueError('This evidence gate requires actual Windows execution')
    report=json.loads((ROOT/'artifacts/neural-review/articulation.json').read_text(encoding='utf-8'))
    corpus=json.loads((ROOT/'tests/fixtures/neural-articulation.json').read_text(encoding='utf-8'))
    if [c['text'] for c in report['sessions']] != [c['text'] for c in corpus['cases']]:
        raise ValueError('Refuse anything except the exact public corpus')
    clips=[]
    for case,clip in zip(corpus['cases'],report['sessions']):
        tts=clip['tts'];analysis=clip['analysis']
        if (tts['providers']!=['CPUExecutionProvider'] or tts['model_sha256']!=MODEL_SHA or tts['voice_sha256']!=VOICE_SHA
            or analysis['platform']!='windows-x64' or analysis['binary_sha256']!=analyzer_profile()['binary_sha256']
            or analysis['audio_sha256']!=clip['audio']['sha256'] or not tts['process_peak_rss_mib'] or tts['process_peak_rss_mib']<=0):
            raise ValueError('Windows CPU/analyzer/memory proof failed')
        clips.append({'case':case['id'],'audio_seconds':clip['duration'],'generation_seconds':clip['generation_seconds'],
            'analysis_seconds':clip['analysis_seconds'],'total_seconds':clip['total_seconds'],
            'peak_working_set_mib':tts['process_peak_rss_mib'],'audio_sha256':clip['audio']['sha256'],
            'analyzer_binary_sha256':analysis['binary_sha256']})
    summary={'platform':'win32','cpu_only':True,'new_recordings':clips,'review_frames':len(report['frames']),
             'estimated_classes':report['observed_classes'],'human_review_completed':False,'target_laptop_tested':False,
             'scope':'Actual Windows hosted CPU inference and exact-WAV/dialog analysis plus live Chrome/WebGL; not laptop or physical AV validation'}
    (ROOT/'artifacts/windows-neural-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if os.environ.get('GITHUB_ACTIONS')=='true':
        text=json.dumps(summary).replace('%','%25').replace('\n','%0A').replace('\r','%0D')
        print('::notice title=Actual Windows neural summary::'+text)


if __name__=='__main__':
    main()
