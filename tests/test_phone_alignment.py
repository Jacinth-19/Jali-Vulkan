"""Synthetic event fixtures only; these tests do not run an acoustic model."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from align_neural_session import normalized_words,phone_windows,crosscheck


class PhoneAlignmentTests(unittest.TestCase):
    def test_normalization_and_explicit_unsupported_text(self):
        self.assertEqual(normalized_words("Mama. Papa! Don't re-use."),['mama','papa',"don't",'re','use'])
        for text in ('','123','Café'):
            with self.assertRaises(ValueError):normalized_words(text)
    def test_phone_and_critical_window_crosscheck(self):
        words=[{'word':'mama','phones':[{'phone':'M','start_frame':0,'frames':5},{'phone':'AA','start_frame':5,'frames':5},{'phone':'L','start_frame':10,'frames':5}]}]
        phones=phone_windows(words,.2)
        result=crosscheck(phones,{'cues':[{'start':0,'end':.025,'value':'A'},{'start':.025,'end':.1,'value':'D'},{'start':.1,'end':.2,'value':'H'}]})
        self.assertEqual(len(result),2);self.assertAlmostEqual(result[0]['estimated_class_coverage'],.5);self.assertEqual(result[1]['estimated_class_coverage'],1)
    def test_empty_overlapping_or_out_of_budget_phones_rejected(self):
        for words in ([],[{'word':'x','phones':[{'phone':'M','start_frame':0,'frames':100}]}],[{'word':'x','phones':[{'phone':'M','start_frame':0,'frames':5},{'phone':'M','start_frame':4,'frames':5}]}]):
            with self.assertRaises(ValueError):phone_windows(words,.2)
