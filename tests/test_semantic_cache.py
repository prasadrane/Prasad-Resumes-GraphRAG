"""
Unit tests for SemanticCache in LLM Gateway.
"""

import math
import time
import unittest
from src.gateway.semantic_cache import SemanticCache, CachedItem


def _cosine(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


class TestSemanticCache(unittest.TestCase):
    """Test suite for semantic cache storage and retrieval."""

    def setUp(self):
        self.cache = SemanticCache(similarity_threshold=0.90, max_size=5, ttl_seconds=2.0)

    def test_exact_match_hit(self):
        self.cache.store("What AWS services did Prasad use?", "Prasad used ECS Fargate, Lambda, DynamoDB.")
        hit = self.cache.lookup("What AWS services did Prasad use?")
        self.assertIsNotNone(hit)
        self.assertIn("ECS Fargate", hit)

    def test_semantic_vector_hit(self):
        # Store with synthetic 4D embedding
        emb1 = [1.0, 0.0, 0.0, 0.0]
        self.cache.store("AWS experience", "Prasad used ECS Fargate.", embedding=emb1)

        # Query with highly similar embedding (cosine > 0.95)
        emb2 = [0.98, 0.02, 0.0, 0.0]
        hit = self.cache.lookup("Tell me about AWS experience", embedding=emb2)
        self.assertIsNotNone(hit)
        self.assertEqual(hit, "Prasad used ECS Fargate.")

    def test_semantic_vector_miss(self):
        emb1 = [1.0, 0.0, 0.0, 0.0]
        self.cache.store("AWS experience", "Prasad used ECS Fargate.", embedding=emb1)

        # Query with orthogonal embedding (cosine = 0.0)
        emb_diff = [0.0, 1.0, 0.0, 0.0]
        hit = self.cache.lookup("What database did he use?", embedding=emb_diff)
        self.assertIsNone(hit)

    def test_lru_eviction(self):
        cache = SemanticCache(similarity_threshold=0.95, max_size=2)
        cache.store("Q1", "A1")
        cache.store("Q2", "A2")
        cache.store("Q3", "A3")  # Evicts Q1

        self.assertIsNone(cache.lookup("Q1"))
        self.assertIsNotNone(cache.lookup("Q2"))
        self.assertIsNotNone(cache.lookup("Q3"))

    def test_ttl_expiration(self):
        cache = SemanticCache(ttl_seconds=0.1)
        cache.store("Q_temp", "A_temp")
        self.assertIsNotNone(cache.lookup("Q_temp"))

        time.sleep(0.15)
        self.assertIsNone(cache.lookup("Q_temp"))


if __name__ == "__main__":
    unittest.main()
