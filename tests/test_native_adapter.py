"""Native/JS speech sampling and cosmetic-layer parity, no rig/GPU/model needed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_visemes import shared_shapes,sample
from native_studio import performance,NativeStudio
from runtime_paths import asset_root,speech_worker_command
ROOT=Path(__file__).resolve().parents[1]


class AdapterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node needed for numerical JS parity')
    def test_js_native_sampler_and_layers_match(self):
        shapes=shared_shapes();clip={'duration':.18,'cues':[{'start':i*.02,'end':(i+1)*.02,'value':v} for i,v in enumerate(shapes)]}
        times=[-.01]+[i/2000 for i in range(370)]
        js="import {sampleClipVisemes,SHAPES} from './web/neural-head/visemes.mjs';import {composePerformance} from './web/neural-head/performance.mjs';const p=JSON.parse((await import('node:fs')).readFileSync(0,'utf8'));console.log(JSON.stringify({samples:p.times.map(t=>sampleClipVisemes(p.clip,t).weights),layers:p.options.map(o=>composePerformance(SHAPES[o.shape].weights,o))}));"
        options=[{'shape':shape,'time':2.55,'duration':4,'mood':mood,'gaze':gaze,'life':life} for shape in shapes for mood in ('neutral','warm','attentive') for gaze in ('forward','left','right','down') for life in (False,True)]
        actual=json.loads(subprocess.check_output(['node','--input-type=module','-e',js],input=json.dumps({'clip':clip,'times':times,'options':options}),cwd=ROOT,text=True))
        for t,expected in zip(times,actual['samples']):
            native=sample(clip,t,shapes);self.assertEqual(native.keys(),expected.keys())
            for k,v in expected.items():self.assertAlmostEqual(native[k],v,places=10)
        for o,expected in zip(options,actual['layers']):
            pose,motion=performance(shapes[o['shape']]['weights'],o['time'],o['duration'],o['life'],o['mood'],o['gaze'])
            self.assertEqual(pose.keys(),expected['pose'].keys())
            for k,v in expected['pose'].items():self.assertAlmostEqual(pose[k],v,places=10)
            for k,v in {'head_yaw':expected['head']['yaw'],'head_roll':expected['head']['roll'],'eye_yaw':expected['eyes']['yaw'],'eye_pitch':expected['eyes']['pitch']}.items():self.assertAlmostEqual(motion[k],v,places=10)
    def test_native_rejects_nonfinite_clock_and_invalid_controls_before_render(self):
        native=NativeStudio.__new__(NativeStudio);native.rig={};native.shapes={'X':{'weights':{}}}
        clip={'rig':{},'duration':1,'cues':[{'start':0,'end':1,'value':'X'}]}
        for query in [{'time':['nan']},{'time':['-1']},{'time':['2']},{'time':['0'],'trim':['151']},{'time':['0'],'life':['maybe']},{'time':['0'],'mood':['inferred']},{'time':['0'],'gaze':['unknown']}]:
            with self.assertRaises(ValueError):native.frame(clip,query)
        with self.assertRaises(ValueError):sample(clip,float('inf'),native.shapes)
    def test_frozen_asset_root_and_worker_dispatch(self):
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS','frozen-assets',create=True):
            self.assertEqual(asset_root(),Path('frozen-assets'))
            self.assertEqual(speech_worker_command(ROOT,['--text','Hello']),[sys.executable,'--speech-worker','--text','Hello'])
        self.assertIn('local_neural_speech.py',speech_worker_command(ROOT,[])[1])
