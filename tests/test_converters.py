"""
Unit tests for resume structurer, text cleaning, and header detection.
"""

import unittest
from src.converters.resume_structurer import clean_text, structure_resume

class TestResumeStructurer(unittest.TestCase):

    def test_clean_text_basic(self):
        raw = "  Hello   World  \n\n\n\nSection 1   "
        expected = "Hello World\n\nSection 1"
        self.assertEqual(clean_text(raw), expected)

    def test_clean_text_multiple_newlines(self):
        raw = "Hello   world!\n\n\nSection"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "Hello world!\n\nSection")

    def test_structure_resume_header_and_sections(self):
        raw_resume = (
            "Prasad Rane\n"
            "Senior Software Engineer\n"
            "prasad@example.com | 123-456-7890\n"
            "SUMMARY\n"
            "Experienced engineer in AI and GraphRAG.\n"
            "SKILLS\n"
            "Python, PyTorch, GraphRAG, LiteLLM\n"
        )
        result = structure_resume(raw_resume)

        self.assertIn("# Prasad Rane", result)
        self.assertIn("**Title:** Senior Software Engineer", result)
        self.assertIn("**Contact:** prasad@example.com | 123-456-7890", result)
        self.assertIn("## SUMMARY", result)
        self.assertIn("Experienced engineer in AI and GraphRAG.", result)
        self.assertIn("## SKILLS", result)
        self.assertIn("Python, PyTorch, GraphRAG, LiteLLM", result)

    def test_structure_resume_empty(self):
        self.assertEqual(structure_resume(""), "")

    def test_structure_resume_with_special_characters_in_headers(self):
        raw_resume = (
            "Prasad Rane\n"
            "TECHNICAL SKILLS & COMPETENCIES\n"
            "C#, .NET Core, AWS\n"
        )
        result = structure_resume(raw_resume)
        self.assertIn("# Prasad Rane", result)
        self.assertIn("## TECHNICAL SKILLS & COMPETENCIES", result)

if __name__ == "__main__":
    unittest.main()
