"""
Regression and helper wrapper tests for convert inputs pipeline.
"""

import unittest
from src.converters.input_converter import make_out_name

class TestConvertInputsLegacy(unittest.TestCase):

    def test_make_out_name_normalization(self):
        self.assertEqual(make_out_name("Prasad Rane (Resume 2024)"), "Prasad_Rane_Resume_2024.txt")

if __name__ == "__main__":
    unittest.main()
