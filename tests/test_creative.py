import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from creative_performance import compose,settings
ROOT=Path(__file__).resolve().parents[1]
class CreativeTests(unittest.TestCase):
    def test_invalid_sequences_and_numeric_types(self):
        for v in [{'intensity':True},{'head':float('nan')},{'natural':1},{'sequence':[{}]},{'seed':.5},{'sequence':[{'start':0,'end':1,'expression':'warm','intensity':1,'fade':2}]}]:
            with self.assertRaises(ValueError):settings(v)
    @unittest.skipUnless(shutil.which('node'),'JS/Python parity requires Node')
    def test_complete_layer_parity_irregular_idle_gaze_expressions_and_boundaries(self):
        cases=[]
        for time in [0,.1,.5,1,1.25,1.5,2,2.7,3.2,4.5,14.12,59.99,60]:
            for natural in [False,True]:
                for idle in [False,True]:
                    cases.append(dict(time=time,duration=60,life=True,mood='serious',gaze='left',creative=dict(natural=natural,idle=idle,idleTime=time,contact=.4,gazeStart=1,gazeEase=1,intensity=.6,sequence=[dict(start=1,end=3,expression='warm',fade=.5,intensity=.7),dict(start=1,end=4,expression='surprise',fade=0,intensity=.4)])))
        program="import {composePerformance} from './web/neural-head/performance.mjs';const cases=JSON.parse((await import('node:fs')).readFileSync(0,'utf8'));console.log(JSON.stringify(cases.map(c=>composePerformance({viseme_PP:.95},c))));"
        actual=json.loads(subprocess.check_output(['node','--input-type=module','-e',program],input=json.dumps(cases),text=True,cwd=ROOT))
        for c,j in zip(cases,actual):
            pose,motion=compose({'viseme_PP':.95},c['time'],c['duration'],c['life'],c['mood'],c['gaze'],c['creative']);self.assertEqual(pose.keys(),j['pose'].keys())
            for k,v in pose.items():self.assertAlmostEqual(v,j['pose'][k],places=11)
            for k,v in [('head_yaw',j['head']['yaw']),('head_roll',j['head']['roll']),('eye_yaw',j['eyes']['yaw']),('eye_pitch',j['eyes']['pitch'])]:self.assertAlmostEqual(motion[k],v,places=11)
