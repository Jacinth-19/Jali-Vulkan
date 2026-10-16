import io
import importlib.util
import threading
import json
from pathlib import Path
import subprocess
import shutil
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_visemes import sample,shared_shapes,articulation
from neural_stream import sentence_batches
from studio_launcher import server_command,diagnostics
ROOT=Path(__file__).resolve().parents[1]


class UpgradeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Numerical JS parity needs Node')
    def test_calibrated_js_python_parity_all_profiles_and_boundaries(self):
        shapes=shared_shapes();clip={'duration':.18,'cues':[{'start':i*.02,'end':(i+1)*.02,'value':v} for i,v in enumerate(shapes)]}
        times=[-.01]+[i/2000 for i in range(381)]
        program="import {sampleClipVisemes} from './web/neural-head/visemes.mjs';const p=JSON.parse((await import('node:fs')).readFileSync(0,'utf8'));console.log(JSON.stringify(p.profiles.map(profile=>p.times.map(t=>sampleClipVisemes(p.clip,t,0,true,profile).weights))));"
        profiles=['baseline','clear','soft',{'closure':1.1,'tongue':1.4,'transition':0,'smooth':True}]
        actual=json.loads(subprocess.check_output(['node','--input-type=module','-e',program],input=json.dumps({'clip':clip,'times':times,'profiles':profiles}),text=True,cwd=ROOT))
        for profile,expected in zip(profiles,actual):
            for t,weights in zip(times,expected):
                value=sample(clip,t,shapes,profile=profile);self.assertEqual(value.keys(),weights.keys())
                for k,v in weights.items():self.assertAlmostEqual(value[k],v,places=10)
    def test_long_text_and_boundaries_stay_bounded_without_relaxing_tts(self):
        text='A longer clause with ordinary words and no stop '*16
        self.assertEqual(sentence_batches('Hello'+(' '*600)),['Hello'])
        with self.assertRaises(ValueError):sentence_batches('Hello'+(' '*499)+'\v')
        parts=sentence_batches(text);self.assertGreater(len(text),500);self.assertLessEqual(len(parts),12);self.assertTrue(all(len(p)<=160 for p in parts))
    def test_overlong_words_invalid_controls_and_thirteenth_chunk_fail(self):
        for text in ['a'*161,'a'*1001,'Hi. '*13,'Bad\x00text']:
            with self.assertRaises(ValueError):sentence_batches(text)
        for profile in [{'closure':float('nan')},{'smooth':1},{'transition':71},'bad']:
            with self.assertRaises(ValueError):articulation(profile)
    def test_launcher_command_frozen_no_external_python_or_node_and_free_port(self):
        with patch.object(sys,'frozen',True,create=True):
            command=server_command('native','low',Path('ready.json'))
        self.assertEqual(command[0],sys.executable);self.assertIn('--native',command);self.assertIn('--no-browser',command);self.assertEqual(command[command.index('--port')+1],'0')
        with self.assertRaises(ValueError):server_command('injected','low',Path('r'))
    def test_doctor_missing_assets_has_repairs_without_downloading(self):
        with patch('local_neural_speech.verify_assets',side_effect=ValueError('missing model')),patch('analyze_neural_clips.verify_engine',side_effect=ValueError('missing analyzer')):
            report=diagnostics(False)
        self.assertTrue(all(not c['ok'] and c['repair'] for c in report['checks']));self.assertIn('not inferred',report['webgl'])

    @unittest.skipUnless(importlib.util.find_spec('PIL'),'JPEG dimensions need Pillow')
    def test_native_actual_jpeg_resize_lock_validation_and_replacement_failure(self):
        from native_studio import NativeStudio
        from PIL import Image
        native=NativeStudio.__new__(NativeStudio);native.rig={};native.shapes=shared_shapes()
        native.asset=Path('test.glb');native.output=Path('output');native.software=False
        native.size=512;native.frame_lock=threading.Lock();native.metadata={};old=native.worker=Mock()
        clip={'rig':{},'duration':1,'cues':[{'start':0,'end':1,'value':'A'}]}
        replacement=Mock();replacement.metadata={};replacement.frame.return_value=(bytes([127])*256*256*4,1.2)
        with patch('native_studio.RichWorker',return_value=replacement):
            jpeg,ms=native.frame(clip,{'time':['0.2'],'resolution':['256']})
        self.assertEqual(Image.open(io.BytesIO(jpeg)).size,(256,256));self.assertEqual(ms,1.2);old.close.assert_called_once()
        with patch('native_studio.RichWorker',side_effect=RuntimeError('driver failure')):
            with self.assertRaises(RuntimeError):native.frame(clip,{'time':['0.2'],'resolution':['768']})
        self.assertIs(native.worker,replacement);self.assertEqual(native.size,256);replacement.close.assert_not_called()
        native.frame_lock.acquire()
        try:
            with self.assertRaises(BlockingIOError):native.frame(clip,{'time':['0.2'],'resolution':['256']})
        finally:native.frame_lock.release()
        for query in [{'time':['nan']},{'time':['0.2'],'resolution':['4096']},{'time':['0.2'],'articulation':['{"closure":9}']}]:
            with self.assertRaises(ValueError):native.frame(clip,query)

    def test_damaged_frozen_doctor_refuses_bundled_native_probe(self):
        with patch.object(sys,'frozen',True,create=True),patch('package_integrity.verify_installation',return_value={'verified':False,'issues':['modified']}),patch('rich_worker.RichWorker') as worker:
            report=diagnostics(True)
        self.assertTrue(report['native_probe_refused']);self.assertFalse(report['checks'][0]['ok']);worker.assert_not_called()
