"""
Unit tests for SME Tech Ontology and Skill Hierarchy module.
"""

import unittest
from src.generators.sme_ontology import SMEOntology


class TestSMEOntology(unittest.TestCase):
    """Test suite for the Subject Matter Expert (SME) Technology Ontology."""

    def setUp(self):
        self.ontology = SMEOntology()

    def test_normalize_term_synonyms(self):
        """Test normalization of common technology synonyms and abbreviations."""
        self.assertEqual(self.ontology.normalize_term("k8s"), "kubernetes")
        self.assertEqual(self.ontology.normalize_term("postgres"), "postgresql")
        self.assertEqual(self.ontology.normalize_term("react.js"), "react")
        self.assertEqual(self.ontology.normalize_term("py-torch"), "pytorch")
        self.assertEqual(self.ontology.normalize_term("golang"), "go")
        self.assertEqual(self.ontology.normalize_term("nodejs"), "node.js")
        self.assertEqual(self.ontology.normalize_term("node js"), "node.js")
        self.assertEqual(self.ontology.normalize_term("k8s / kubernetes"), "kubernetes")

    def test_normalize_term_casing_and_whitespace(self):
        """Test normalization with irregular casing, leading/trailing whitespace."""
        self.assertEqual(self.ontology.normalize_term("  K8s  "), "kubernetes")
        self.assertEqual(self.ontology.normalize_term("PostgreSQL"), "postgresql")
        self.assertEqual(self.ontology.normalize_term("  REACT.JS  "), "react")
        self.assertEqual(self.ontology.normalize_term("Py-Torch"), "pytorch")
        self.assertEqual(self.ontology.normalize_term("FastAPI"), "fastapi")

    def test_normalize_term_unknown_and_edge_cases(self):
        """Test normalization of unknown terms, empty strings, and None."""
        self.assertEqual(self.ontology.normalize_term("unknown_tech_xyz"), "unknown_tech_xyz")
        self.assertEqual(self.ontology.normalize_term("  Some Custom Tool  "), "some custom tool")
        self.assertEqual(self.ontology.normalize_term(""), "")
        self.assertEqual(self.ontology.normalize_term(None), "")

    def test_get_parent_categories_pytorch(self):
        """Test parent category extraction for PyTorch."""
        categories = self.ontology.get_parent_categories("pytorch")
        self.assertTrue(any("Deep Learning" in cat for cat in categories))
        self.assertTrue(any("Machine Learning" in cat or "AI/ML" in cat for cat in categories))

    def test_get_parent_categories_fastapi(self):
        """Test parent category extraction for FastAPI."""
        categories = self.ontology.get_parent_categories("fastapi")
        self.assertTrue(any("REST" in cat or "API" in cat for cat in categories))
        self.assertTrue(any("Backend" in cat or "Microservices" in cat for cat in categories))

    def test_get_parent_categories_kafka(self):
        """Test parent category extraction for Kafka."""
        categories = self.ontology.get_parent_categories("kafka")
        self.assertTrue(any("Event-Driven" in cat or "Event" in cat for cat in categories))
        self.assertTrue(any("Streaming" in cat or "Message" in cat or "Distributed" in cat for cat in categories))

    def test_get_parent_categories_fargate(self):
        """Test parent category extraction for AWS Fargate."""
        categories = self.ontology.get_parent_categories("fargate")
        self.assertTrue(any("Container" in cat for cat in categories))
        self.assertTrue(any("Serverless" in cat or "AWS" in cat or "Cloud" in cat for cat in categories))

    def test_get_parent_categories_casing_and_unknown(self):
        """Test get_parent_categories with mixed case and unknown terms."""
        categories_upper = self.ontology.get_parent_categories("  PYTORCH  ")
        self.assertGreater(len(categories_upper), 0)
        self.assertEqual(self.ontology.get_parent_categories("non_existent_tool_123"), [])
        self.assertEqual(self.ontology.get_parent_categories(""), [])
        self.assertEqual(self.ontology.get_parent_categories(None), [])

    def test_get_child_skills(self):
        """Test child skill retrieval by parent category or high-level skill."""
        dl_children = self.ontology.get_child_skills("deep learning")
        self.assertIn("pytorch", dl_children)
        self.assertIn("tensorflow", dl_children)

        event_children = self.ontology.get_child_skills("event streaming")
        self.assertTrue("kafka" in event_children or "rabbitmq" in event_children)

        self.assertEqual(self.ontology.get_child_skills("non_existent_category"), [])
        self.assertEqual(self.ontology.get_child_skills(""), [])

    def test_expand_query_terms_high_level(self):
        """Test query term expansion from high-level categories to specific skills."""
        expanded = self.ontology.expand_query_terms(["deep learning"])
        self.assertIn("deep learning", expanded)
        self.assertIn("pytorch", expanded)
        self.assertIn("tensorflow", expanded)

    def test_expand_query_terms_event_streaming(self):
        """Test query term expansion for event streaming and message brokers."""
        expanded = self.ontology.expand_query_terms(["event streaming"])
        self.assertIn("event streaming", expanded)
        self.assertTrue("kafka" in expanded or "rabbitmq" in expanded or "kinesis" in expanded)

    def test_expand_query_terms_synonyms_and_specific(self):
        """Test expanding specific skills or abbreviations."""
        expanded = self.ontology.expand_query_terms(["k8s", "postgres"])
        self.assertIn("kubernetes", expanded)
        self.assertIn("postgresql", expanded)

    def test_expand_query_terms_empty_and_unknown(self):
        """Test expanding empty input or unknown terms."""
        self.assertEqual(self.ontology.expand_query_terms([]), [])
        self.assertEqual(self.ontology.expand_query_terms(["some_obscure_tech"]), ["some_obscure_tech"])

    def test_are_related_synonyms(self):
        """Test relatedness check between synonyms."""
        self.assertTrue(self.ontology.are_related("k8s", "kubernetes"))
        self.assertTrue(self.ontology.are_related("postgres", "postgresql"))
        self.assertTrue(self.ontology.are_related("py-torch", "pytorch"))

    def test_are_related_shared_domain_and_siblings(self):
        """Test relatedness check between sibling technologies sharing a domain."""
        self.assertTrue(self.ontology.are_related("pytorch", "tensorflow"))
        self.assertTrue(self.ontology.are_related("kafka", "rabbitmq"))
        self.assertTrue(self.ontology.are_related("fastapi", "flask"))
        self.assertTrue(self.ontology.are_related("docker", "kubernetes"))

    def test_are_related_parent_child(self):
        """Test relatedness check between parent categories and child skills."""
        self.assertTrue(self.ontology.are_related("fastapi", "microservices"))
        self.assertTrue(self.ontology.are_related("fargate", "aws"))
        self.assertTrue(self.ontology.are_related("deep learning", "pytorch"))

    def test_are_related_unrelated_terms(self):
        """Test that unrelated technologies return False."""
        self.assertFalse(self.ontology.are_related("pytorch", "django"))
        self.assertFalse(self.ontology.are_related("fargate", "pytorch"))
        self.assertFalse(self.ontology.are_related("unknown_a", "unknown_b"))

    def test_are_related_edge_cases(self):
        """Test relatedness with identical terms, empty strings, and None."""
        self.assertTrue(self.ontology.are_related("react", "react"))
        self.assertTrue(self.ontology.are_related("  REACT  ", "react"))
        self.assertFalse(self.ontology.are_related("", "kubernetes"))
        self.assertFalse(self.ontology.are_related(None, "kubernetes"))
        self.assertFalse(self.ontology.are_related("kubernetes", None))

    def test_static_or_class_access(self):
        """Test that utility methods are accessible statically or via class instance."""
        self.assertEqual(SMEOntology.normalize("k8s"), "kubernetes")
        categories = SMEOntology.get_categories("pytorch")
        self.assertTrue(len(categories) > 0)


if __name__ == "__main__":
    unittest.main()
