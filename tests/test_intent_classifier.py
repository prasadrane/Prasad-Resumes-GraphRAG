"""
Unit tests for IntentClassifier and QueryIntent enum.
"""

import unittest
from src.query.intent_classifier import IntentClassifier, QueryIntent
from src.generators.sme_ontology import SMEOntology


class TestQueryIntentEnum(unittest.TestCase):
    """Test QueryIntent enum definitions."""

    def test_enum_members_exist(self):
        expected_members = {
            "SKILL_LOOKUP": "skill_lookup",
            "COMPANY_LOOKUP": "company_lookup",
            "EXPERIENCE_LOOKUP": "experience_lookup",
            "METRICS_LOOKUP": "metrics_lookup",
            "COMPARATIVE_QUERY": "comparative_query",
            "GENERAL_QUERY": "general_query",
        }
        for name, value in expected_members.items():
            self.assertTrue(hasattr(QueryIntent, name), f"QueryIntent missing member {name}")
            self.assertEqual(getattr(QueryIntent, name).value, value)


class TestIntentClassifierClassification(unittest.TestCase):
    """Test IntentClassifier.classify behavior across intent categories."""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_metrics_lookup_classification(self):
        metrics_queries = [
            "What were Prasad's cost savings at Rocket Mortgage?",
            "Show me performance metrics and scale numbers",
            "What percentage reduction was achieved?",
            "What was the latency reduction and throughput improvement?",
            "What was the quantitative impact and ROI of his projects?",
            "Show me dollar savings and benchmark statistics",
        ]
        for query in metrics_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.METRICS_LOOKUP)

    def test_comparative_query_classification(self):
        comparative_queries = [
            "Compare Prasad's experience at Rocket Mortgage vs London Computer Systems",
            "Compare AWS vs .NET experience",
            "How does his leadership compare across companies?",
            "What is the difference between his work at Rocket Mortgage and LCS?",
            "Compare Python versus Java projects",
        ]
        for query in comparative_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.COMPARATIVE_QUERY)

    def test_skill_lookup_classification(self):
        skill_queries = [
            "What AWS technologies has Prasad used?",
            "Tell me about his python and docker skills",
            "Does Prasad have experience with Kubernetes and Terraform?",
            "List his frontend tools and tech stack",
            "What databases does he know?",
        ]
        for query in skill_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.SKILL_LOOKUP)

    def test_company_lookup_classification(self):
        company_queries = [
            "Where did Prasad work?",
            "What companies has he worked for?",
            "Who was his employer before Rocket Mortgage?",
            "What is his career history?",
            "Where has he been employed?",
        ]
        for query in company_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.COMPANY_LOOKUP)

    def test_experience_lookup_classification(self):
        experience_queries = [
            "Tell me about Prasad's experience building microservices",
            "Describe his background leading backend engineering teams",
            "What projects has Prasad built and managed?",
            "Describe the architecture he designed",
        ]
        for query in experience_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.EXPERIENCE_LOOKUP)

    def test_general_query_classification(self):
        general_queries = [
            "Hello there",
            "What is Prasad's education?",
            "Tell me about his certifications",
            "Give me a summary of Prasad",
            "",
            "   ",
            "hi",
        ]
        for query in general_queries:
            with self.subTest(query=query):
                intent = self.classifier.classify(query)
                self.assertEqual(intent, QueryIntent.GENERAL_QUERY)

    def test_ontology_integration_recognition(self):
        # Query mentioning ontology synonyms and specialized tech terms
        query_k8s = "What k8s and py-torch skills does he have?"
        self.assertEqual(self.classifier.classify(query_k8s), QueryIntent.SKILL_LOOKUP)

        query_ontology_category = "Tell me about his cloud & infrastructure experience"
        # Should classify cleanly
        intent = self.classifier.classify(query_ontology_category)
        self.assertIn(intent, [QueryIntent.SKILL_LOOKUP, QueryIntent.EXPERIENCE_LOOKUP])


class TestRetrievalStrategy(unittest.TestCase):
    """Test IntentClassifier.get_retrieval_strategy."""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_all_intents_have_valid_strategy(self):
        valid_modes = {"local", "global", "drift"}
        for intent in QueryIntent:
            with self.subTest(intent=intent):
                strategy = self.classifier.get_retrieval_strategy(intent)
                self.assertIsInstance(strategy, dict)
                self.assertIn("mode", strategy)
                self.assertIn(strategy["mode"], valid_modes)
                self.assertIn("top_k", strategy)
                self.assertIsInstance(strategy["top_k"], int)
                self.assertGreater(strategy["top_k"], 0)
                self.assertIn("entity_boost", strategy)
                self.assertIsInstance(strategy["entity_boost"], bool)
                self.assertIn("enable_guardrail", strategy)
                self.assertTrue(strategy["enable_guardrail"])
                self.assertIn("fallback_mode", strategy)
                self.assertIn(strategy["fallback_mode"], valid_modes)
                self.assertIn("description", strategy)

    def test_specific_intent_strategies(self):
        skill_strat = self.classifier.get_retrieval_strategy(QueryIntent.SKILL_LOOKUP)
        self.assertEqual(skill_strat["mode"], "local")
        self.assertTrue(skill_strat["entity_boost"])
        self.assertTrue(skill_strat["enable_guardrail"])
        self.assertEqual(skill_strat["fallback_mode"], "global")

        company_strat = self.classifier.get_retrieval_strategy(QueryIntent.COMPANY_LOOKUP)
        self.assertEqual(company_strat["mode"], "global")
        self.assertFalse(company_strat["entity_boost"])
        self.assertTrue(company_strat["enable_guardrail"])
        self.assertEqual(company_strat["fallback_mode"], "local")

        metrics_strat = self.classifier.get_retrieval_strategy(QueryIntent.METRICS_LOOKUP)
        self.assertEqual(metrics_strat["mode"], "local")
        self.assertTrue(metrics_strat["entity_boost"])
        self.assertTrue(metrics_strat["enable_guardrail"])

        comp_strat = self.classifier.get_retrieval_strategy(QueryIntent.COMPARATIVE_QUERY)
        self.assertIn(comp_strat["mode"], ["global", "drift"])
        self.assertTrue(comp_strat["enable_guardrail"])


class TestClassifyWithDetails(unittest.TestCase):
    """Test IntentClassifier.classify_with_details."""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_details_structure_and_types(self):
        query = "What AWS and Docker skills does Prasad have?"
        details = self.classifier.classify_with_details(query)
        
        self.assertIsInstance(details, dict)
        self.assertIn("intent", details)
        self.assertIn("primary_intent", details)
        self.assertEqual(details["primary_intent"], QueryIntent.SKILL_LOOKUP.value)
        self.assertIn("confidence", details)
        self.assertIsInstance(details["confidence"], float)
        self.assertGreaterEqual(details["confidence"], 0.0)
        self.assertLessEqual(details["confidence"], 1.0)
        self.assertIn("extracted_entities", details)
        self.assertIsInstance(details["extracted_entities"], list)
        self.assertIn("suggested_strategy", details)
        self.assertIsInstance(details["suggested_strategy"], dict)
        self.assertTrue(details["suggested_strategy"]["enable_guardrail"])

    def test_extracted_entities_via_ontology(self):
        query = "What AWS, Docker, and PyTorch technologies has he used?"
        details = self.classifier.classify_with_details(query)
        extracted = [e.lower() for e in details["extracted_entities"]]
        self.assertIn("aws", extracted)
        self.assertIn("docker", extracted)
        self.assertIn("pytorch", extracted)

    def test_extracted_entities_with_synonyms(self):
        query = "Compare k8s vs py-torch performance"
        details = self.classifier.classify_with_details(query)
        extracted = [e.lower() for e in details["extracted_entities"]]
        self.assertTrue("kubernetes" in extracted or "k8s" in extracted)
        self.assertTrue("pytorch" in extracted or "py-torch" in extracted)

    def test_empty_query_details(self):
        details = self.classifier.classify_with_details("")
        self.assertEqual(details["primary_intent"], QueryIntent.GENERAL_QUERY.value)
        self.assertAlmostEqual(details["confidence"], 0.0, places=2)
        self.assertEqual(details["extracted_entities"], [])


if __name__ == "__main__":
    unittest.main()
