"""Fast M1 admission tests: no NumPy, model downloads or inference required."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from local_neural_speech import validate_request, verify_assets
from prepare_kokoro_cpu import digest


class LocalNeuralTests(unittest.TestCase):
    def test_accept_new_text(self):
        validate_request('A new sentence, not a pre-recorded fixture.')
        validate_request('Hello.\nThis is Jali.', 0.5, 1)
        validate_request('Another example.', 2, 8)

    def test_reject_missing_and_oversized_text(self):
        for text in ('', ' \n\t', 'a' * 501, None, 123):
            with self.subTest(text=str(text)[:20]):
                with self.assertRaises(ValueError):
                    validate_request(text)

    def test_reject_control_characters(self):
        with self.assertRaises(ValueError):
            validate_request('Hello\0hidden')

    def test_reject_invalid_speed(self):
        for speed in (-1, 0.49, 2.01, float('nan'), float('inf'), True, '1'):
            with self.assertRaises(ValueError):
                validate_request('Hello', speed)

    def test_reject_invalid_thread_budget(self):
        for threads in (0, 9, True, 1.5, '2'):
            with self.assertRaises(ValueError):
                validate_request('Hello', threads=threads)

    def test_missing_and_tampered_assets_fail_before_inference(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaises(ValueError):
                verify_assets(root)
            (root / 'model_quantized.onnx').write_bytes(b'not a reviewed model')
            with self.assertRaises(ValueError):
                verify_assets(root)

    def test_streaming_sha256(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'input'
            path.write_bytes(b'abc')
            self.assertEqual(digest(path), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')


if __name__ == '__main__':
    unittest.main()
