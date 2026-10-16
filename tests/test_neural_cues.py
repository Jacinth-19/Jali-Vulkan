"""Model-free admission tests; do not install or execute the speech recognizer."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_neural_clips import validate_timeline


class NeuralCueTests(unittest.TestCase):
    def setUp(self):
        self.data = {'metadata': {'duration': 1.0}, 'mouthCues': [
            {'start': 0.0, 'end': 0.2, 'value': 'X'},
            {'start': 0.2, 'end': 0.6, 'value': 'A'},
            {'start': 0.6, 'end': 1.0, 'value': 'D'}]}

    def test_valid_audio_coverage(self):
        self.assertEqual(len(validate_timeline(self.data, 1)), 3)

    def test_reject_wrong_recording_duration(self):
        with self.assertRaises(ValueError):
            validate_timeline(self.data, 1.2)

    def test_reject_gap_and_overlap(self):
        for start in (0.1, 0.4):
            data = copy.deepcopy(self.data)
            data['mouthCues'][1]['start'] = start
            with self.assertRaises(ValueError):
                validate_timeline(data, 1)

    def test_reject_unknown_mouth_class(self):
        self.data['mouthCues'][1]['value'] = 'not-a-viseme'
        with self.assertRaises(ValueError):
            validate_timeline(self.data, 1)

    def test_reject_nonfinite_cues_and_metadata(self):
        for target in ('cue', 'metadata'):
            data = copy.deepcopy(self.data)
            if target == 'cue':
                data['mouthCues'][0]['end'] = float('nan')
            else:
                data['metadata']['duration'] = float('nan')
            with self.assertRaises(ValueError):
                validate_timeline(data, 1)

    def test_reject_truncated_or_empty_cues(self):
        for cues in ([], self.data['mouthCues'][:-1]):
            self.data['mouthCues'] = cues
            with self.assertRaises(ValueError):
                validate_timeline(self.data, 1)


if __name__ == '__main__':
    unittest.main()
