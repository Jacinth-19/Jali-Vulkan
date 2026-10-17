import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_independent_reference import compare

class IndependentReferenceTests(unittest.TestCase):
    def setUp(self):
        self.clip={'audio':{'sha256':'a'*64},'text_sha256':'b'*64,'duration':2,'cues':[{'start':.4,'end':.8,'value':'A'}]}
        self.reference={'schema':'jali-independent-phone-reference-v1','audio_sha256':'a'*64,'text_sha256':'b'*64,'provenance':{'kind':'manual-phonetic-annotation','tool':'synthetic unit fixture','annotator_or_model':'test only','method':'explicit synthetic annotation, not independent quality evidence','source':'unit fixture'},'phones':[{'phone':'P','start':.5,'end':.7,'uncertainty_ms':10}]}
    def test_explicit_fixture_compares_but_never_approves_quality_or_physics(self):
        r=compare(self.reference,self.clip);self.assertEqual(r['rows'][0]['estimated_class_coverage'],1);self.assertAlmostEqual(r['rows'][0]['nearest_estimated_start_error_ms'],-100);self.assertFalse(r['human_quality_accepted']);self.assertFalse(r['physical_av_measured'])
    def test_wrong_hash_related_method_and_bad_intervals_rejected(self):
        for key,value in [('audio_sha256','c'*64),('text_sha256','c'*64)]:
            r=copy.deepcopy(self.reference);r[key]=value
            with self.assertRaises(ValueError):compare(r,self.clip)
        for method in ['PocketSphinx','CMU Sphinx','Rhubarb']:
            r=copy.deepcopy(self.reference);r['provenance']['tool']=method
            with self.assertRaises(ValueError):compare(r,self.clip)
        for value in [float('nan'),True,-1,3]:
            r=copy.deepcopy(self.reference);r['phones'][0]['end']=value
            with self.assertRaises(ValueError):compare(r,self.clip)
    def test_av_sign_uncertainty_and_no_synthetic_acceptance(self):
        try:from measure_recorded_av import summarize
        except ImportError:self.skipTest('Optional NumPy recording-analysis dependency absent')
        r=summarize([.62,1.62,2.62],[.5,1.5,2.5]);self.assertAlmostEqual(r['median_observed_offset_ms'],120);self.assertFalse(r['physical_av_accepted']);self.assertIsNone(r['corrected_output_offset_ms']);self.assertGreaterEqual(r['minimum_timing_uncertainty_ms'],40)
        c=summarize([.62,1.62,2.62],[.5,1.5,2.5],physical=True,capture_offset_ms=20,capture_uncertainty_ms=5);self.assertAlmostEqual(c['corrected_output_offset_ms'],100);self.assertFalse(c['physical_av_accepted'])
        with self.assertRaises(ValueError):summarize([.6],[.5])
        with self.assertRaises(ValueError):summarize([.6,1.6,2.9],[.5,1.5,2.5])
    def test_real_container_pts_synthetic_fixture_is_not_physical_evidence(self):
        try:
            import imageio_ffmpeg
            from measure_recorded_av import analyze
        except ImportError:self.skipTest('Optional NumPy/FFmpeg recording-analysis dependencies absent')
        import subprocess,tempfile
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'synthetic.mp4'
            video="color=black:s=160x120:r=60:d=4,drawbox=color=white:t=fill:enable='between(t,0.5,0.62)+between(t,1.5,1.62)+between(t,2.5,2.62)'"
            audio="aevalsrc='0.2*sin(2*PI*1200*t)*(between(t,0.62,0.74)+between(t,1.62,1.74)+between(t,2.62,2.74))':s=48000:d=4"
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','lavfi','-i',video,'-itsoffset','0.1','-f','lavfi','-i',audio,'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(file)],check=True,capture_output=True,timeout=30)
            result=analyze(file,[8,8,100,80]);self.assertAlmostEqual(result['median_observed_offset_ms'],220,delta=20);self.assertFalse(result['physical_av_accepted']);self.assertEqual(len(result['visual_onsets_seconds']),3)
