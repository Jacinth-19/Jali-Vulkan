import copy
import hashlib
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from evaluate_articulation import evaluate
from audit_native_rig import audit
from benchmark_neural import run
import neural_studio_server as studio


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        text='Public test'
        self.clip={'duration':1.,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'audio':{'sha256':'a'*64},'cues':[{'start':0.,'end':.2,'value':'X'},{'start':.2,'end':.5,'value':'A'},{'start':.5,'end':1.,'value':'D'}]}
        self.ref={'audio_sha256':'a'*64,'text_sha256':self.clip['text_sha256'],'method':'manual-listening-waveform','reviewer':'unit-test fixture, not human QA','source':'explicit synthetic reference','independent_of_rhubarb':True,'events':[{'start':.21,'end':.49,'class':'A','uncertainty_seconds':.02}]}

    def test_event_errors_are_signed_and_scoped(self):
        r=evaluate(self.ref,self.clip);e=r['events'][0]
        self.assertAlmostEqual(e['onset_error_seconds'],-.01);self.assertAlmostEqual(e['offset_error_seconds'],.01)
        self.assertEqual(e['estimated_class_coverage'],1);self.assertTrue(e['boundaries_within_declared_uncertainty'])
        self.assertFalse(r['reference_independence_verified_by_tool']);self.assertIsNone(r['quality_score'])

    def test_missing_class_does_not_invent_boundary_error(self):
        self.ref['events'][0]['class']='G';e=evaluate(self.ref,self.clip)['events'][0]
        self.assertEqual(e['estimated_class_coverage'],0);self.assertIsNone(e['onset_error_seconds'])

    def test_pending_or_unattributed_reference_refused(self):
        for key,value in [('events',[]),('method',None),('independent_of_rhubarb',False),('reviewer',''),('source',''),('audio_sha256','b'*64),('text_sha256','other')]:
            ref=copy.deepcopy(self.ref);ref[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):evaluate(ref,self.clip)

    def test_invalid_times_labels_and_overlaps_refused(self):
        for key,value in [('start',float('nan')),('end',float('inf')),('start',True),('class','bad'),('uncertainty_seconds',.3),('start',.6)]:
            ref=copy.deepcopy(self.ref);ref['events'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):evaluate(ref,self.clip)
        self.ref['events']*=2
        with self.assertRaises(ValueError):evaluate(self.ref,self.clip)

    def test_untrusted_clip_timeline_refused(self):
        self.clip['cues'][0]['end']=.8
        with self.assertRaises(ValueError):evaluate(self.ref,self.clip)


class NativeAuditTests(unittest.TestCase):
    def test_realistic_large_rig_is_incompatible_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as directory:
            model={'extensionsRequired':['EXT_meshopt_compression'],'skins':[{'joints':list(range(67))}],
                'meshes':[{'extras':{'targetNames':['viseme_PP']},'primitives':[{'targets':[{}]*66}]}],
                'materials':[{}],'images':[{}],'accessors':[{'componentType':5122}]}
            data=json.dumps(model).encode();data+=b' '*((-len(data))%4)
            path=Path(directory)/'test.glb';path.write_bytes(b'glTF'+struct.pack('<IIII',2,len(data)+20,len(data),0x4e4f534a)+data)
            r=audit(path);self.assertEqual(r['counts']['max_skin_joints'],67)
            self.assertEqual(r['static_status'],'known_incompatible');self.assertFalse(r['native_rendering_performed']);self.assertFalse(r['assets_modified'])
            self.assertIn('palette_64_limit',[b['code'] for b in r['blockers']])


class BenchmarkSafetyTests(unittest.TestCase):
    def test_invalid_budget_fails_before_starting_any_process(self):
        for repeats in (0,4,True):
            with self.assertRaises(ValueError):run(repeats)

    def test_busy_port_does_not_delete_existing_sessions(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket() as occupied:
            occupied.bind(('127.0.0.1',0));occupied.listen()
            root=Path(directory);assets=root/'artifacts/neural-studio';assets.mkdir(parents=True)
            for name in ('index.html','viewer.js','controller.js','demo-data.js'): (assets/name).write_text('fixture')
            (assets/'rig.json').write_text(json.dumps({'model_sha256':'hash','viewer_sha256':'hash'}))
            sessions=root/'sessions';old=sessions/('a'*32);old.mkdir(parents=True);(old/'keep.txt').write_text('keep')
            with patch.object(studio,'ROOT',root),patch.object(studio,'digest',return_value='hash'),patch.object(studio,'verify_assets'),patch.object(studio,'verify_engine'),patch.object(studio,'analyzer_path',return_value=root/'analyzer'),patch.object(sys,'argv',['server','--bind','127.0.0.1','--port',str(occupied.getsockname()[1]),'--sessions',str(sessions)]):
                with self.assertRaises(OSError):studio.main()
            self.assertEqual((old/'keep.txt').read_text(),'keep')
