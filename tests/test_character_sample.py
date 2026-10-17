import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_character_sample import prepare
class CharacterSampleTests(unittest.TestCase):
    def test_download_requires_explicit_personal_acknowledgement(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'sample'
            with self.assertRaisesRegex(ValueError,'personal-noncommercial'):
                prepare(output,False)
            self.assertFalse(output.exists())
