"""
Unit tests for PII Redactor and Data Privacy Guardrails.
"""

import unittest
from src.security.pii_redactor import PIIRedactor, PIIRedactionResult


class TestPIIRedactor(unittest.TestCase):
    """Test suite for PII detection, redaction, and restoration."""

    def setUp(self):
        self.redactor = PIIRedactor()

    def test_email_redaction_and_restore(self):
        text = "Contact Prasad at prasad.rane@example.com for software roles."
        res = self.redactor.redact(text)
        self.assertIsInstance(res, PIIRedactionResult)
        self.assertNotIn("prasad.rane@example.com", res.redacted_text)
        self.assertIn("[EMAIL_1]", res.redacted_text)
        self.assertIn("email", res.found_types)

        # Restoration check
        restored = self.redactor.restore(res.redacted_text, res.mapping)
        self.assertEqual(restored, text)

    def test_phone_redaction_and_restore(self):
        text = "Reach me at (312) 555-0199 or +1-800-555-1234."
        res = self.redactor.redact(text)
        self.assertNotIn("312", res.redacted_text)
        self.assertIn("[PHONE_", res.redacted_text)

        restored = self.redactor.restore(res.redacted_text, res.mapping)
        self.assertEqual(restored, text)

    def test_clean_text_no_pii(self):
        text = "Architected AWS ECS Fargate microservices with Kafka streaming."
        res = self.redactor.redact(text)
        self.assertEqual(res.redacted_text, text)
        self.assertEqual(len(res.mapping), 0)
        self.assertEqual(len(res.found_types), 0)

    def test_empty_input(self):
        res = self.redactor.redact("")
        self.assertEqual(res.redacted_text, "")
        self.assertEqual(self.redactor.restore("", {}), "")


if __name__ == "__main__":
    unittest.main()
