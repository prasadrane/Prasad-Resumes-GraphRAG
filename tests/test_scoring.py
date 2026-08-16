"""
tests/test_scoring.py — Unit tests for Action-Verb Impact Scoring & Recency Decay Engine.
"""

import unittest
import math
from src.generators.scoring import ImpactScorer, ScoreBreakdown


class TestImpactScorerVerbTiers(unittest.TestCase):
    """Test action-verb tier classification and scoring."""

    def setUp(self):
        self.scorer = ImpactScorer()

    def test_tier_1_verbs(self):
        tier_1_verbs = [
            "architected",
            "spearheaded",
            "engineered",
            "orchestrated",
            "pioneered",
            "designed",
            "founded",
            "transformed",
        ]
        for verb in tier_1_verbs:
            bullet = f"{verb.capitalize()} a scalable distributed system for real-time stream processing."
            tier = ImpactScorer.get_verb_tier(bullet)
            score = ImpactScorer.get_verb_score(bullet)
            self.assertEqual(tier, 1, f"Expected Tier 1 for '{verb}', got {tier}")
            self.assertAlmostEqual(score, 1.0, places=2, msg=f"Expected score 1.0 for '{verb}', got {score}")

    def test_tier_2_verbs(self):
        tier_2_verbs = [
            "implemented",
            "developed",
            "built",
            "optimized",
            "migrated",
            "scaled",
            "delivered",
            "automated",
            "integrated",
        ]
        for verb in tier_2_verbs:
            bullet = f"{verb.capitalize()} cloud microservices to improve deployment reliability."
            tier = ImpactScorer.get_verb_tier(bullet)
            score = ImpactScorer.get_verb_score(bullet)
            self.assertEqual(tier, 2, f"Expected Tier 2 for '{verb}', got {tier}")
            self.assertAlmostEqual(score, 0.7, places=2, msg=f"Expected score 0.7 for '{verb}', got {score}")

    def test_tier_3_verbs(self):
        tier_3_verbs = [
            "maintained",
            "supported",
            "assisted",
            "monitored",
            "updated",
            "documented",
            "troubleshot",
        ]
        for verb in tier_3_verbs:
            bullet = f"{verb.capitalize()} internal infrastructure and resolved tier-2 tickets."
            tier = ImpactScorer.get_verb_tier(bullet)
            score = ImpactScorer.get_verb_score(bullet)
            self.assertEqual(tier, 3, f"Expected Tier 3 for '{verb}', got {tier}")
            self.assertAlmostEqual(score, 0.4, places=2, msg=f"Expected score 0.4 for '{verb}', got {score}")

    def test_fallback_verbs(self):
        fallback_verbs = ["researched", "analyzed", "reviewed", "attended", "participated"]
        for verb in fallback_verbs:
            bullet = f"{verb.capitalize()} customer feedback reports."
            tier = ImpactScorer.get_verb_tier(bullet)
            score = ImpactScorer.get_verb_score(bullet)
            self.assertEqual(tier, 0, f"Expected Fallback Tier 0 for '{verb}', got {tier}")
            self.assertAlmostEqual(score, 0.5, places=2, msg=f"Expected fallback score 0.5 for '{verb}', got {score}")

    def test_bullet_formatting_handling(self):
        bullets = [
            "- **Architected** enterprise data lake",
            "• Spearheaded cross-functional migration",
            "1. Engineered high-availability clusters",
            "   * Transformed legacy monolith",
        ]
        for bullet in bullets:
            tier = ImpactScorer.get_verb_tier(bullet)
            score = ImpactScorer.get_verb_score(bullet)
            self.assertEqual(tier, 1)
            self.assertAlmostEqual(score, 1.0)


class TestImpactScorerMetricDetection(unittest.TestCase):
    """Test metric extraction and metric bonus calculation."""

    def test_detect_percentages(self):
        bullet = "Optimized database queries, reducing query response time by 70% and memory usage by 40%."
        metrics = ImpactScorer.detect_metrics(bullet)
        self.assertTrue(any("70%" in m for m in metrics))
        self.assertTrue(any("40%" in m for m in metrics))
        bonus = ImpactScorer.get_metric_bonus(bullet)
        self.assertAlmostEqual(bonus, 0.2, places=2)

    def test_detect_currency(self):
        bullet_1 = "Delivered automated cost-optimization system saving $1.2M annually across AWS accounts."
        metrics_1 = ImpactScorer.detect_metrics(bullet_1)
        self.assertTrue(any("$1.2M" in m for m in metrics_1))

        bullet_2 = "Managed infrastructure budget of $500K with zero overages."
        metrics_2 = ImpactScorer.detect_metrics(bullet_2)
        self.assertTrue(any("$500K" in m for m in metrics_2))

        bonus = ImpactScorer.get_metric_bonus(bullet_1)
        self.assertAlmostEqual(bonus, 0.2, places=2)

    def test_detect_latency_and_speedup(self):
        bullet_1 = "Reduced API latency from 250ms to 50ms for mission-critical endpoints."
        metrics_1 = ImpactScorer.detect_metrics(bullet_1)
        self.assertTrue(any("50ms" in m for m in metrics_1) or any("250ms" in m for m in metrics_1))

        bullet_2 = "Achieved 2.5x throughput improvement and 10x faster model inference."
        metrics_2 = ImpactScorer.detect_metrics(bullet_2)
        self.assertTrue(any("2.5x" in m.lower() for m in metrics_2))
        self.assertTrue(any("10x" in m.lower() for m in metrics_2))

    def test_detect_scale_indicators(self):
        bullet_1 = "Engineered authentication service scaling to 10k users concurrently."
        metrics_1 = ImpactScorer.detect_metrics(bullet_1)
        self.assertTrue(any("10k users" in m.lower() for m in metrics_1))

        bullet_2 = "Handled over 5M requests daily with 99.99% uptime."
        metrics_2 = ImpactScorer.detect_metrics(bullet_2)
        self.assertTrue(any("5m requests" in m.lower() for m in metrics_2))

        bullet_3 = "Migrated 100+ microservices to Kubernetes cluster."
        metrics_3 = ImpactScorer.detect_metrics(bullet_3)
        self.assertTrue(any("100+ microservices" in m.lower() for m in metrics_3))

    def test_no_metrics_returns_zero_bonus(self):
        bullet = "Maintained documentation and assisted team members with onboarding."
        metrics = ImpactScorer.detect_metrics(bullet)
        self.assertEqual(len(metrics), 0)
        bonus = ImpactScorer.get_metric_bonus(bullet)
        self.assertAlmostEqual(bonus, 0.0, places=2)


class TestImpactScorerRecencyDecay(unittest.TestCase):
    """Test exponential recency decay calculation."""

    def test_recent_work_2026_and_2025(self):
        # delta_t = 0 -> e^0 = 1.0
        decay_2026 = ImpactScorer.calculate_recency_decay(
            start_year=2024, end_year=2026, reference_year=2026, lambda_decay=0.15
        )
        self.assertAlmostEqual(decay_2026, 1.0, places=2)

        # delta_t = 1 -> e^(-0.15) ≈ 0.8607
        decay_2025 = ImpactScorer.calculate_recency_decay(
            start_year=2023, end_year=2025, reference_year=2026, lambda_decay=0.15
        )
        expected_2025 = math.exp(-0.15 * 1)
        self.assertAlmostEqual(decay_2025, expected_2025, places=2)
        self.assertTrue(0.85 <= decay_2025 <= 0.87)

    def test_mid_career_work_2021(self):
        # delta_t = 5 -> e^(-0.15 * 5) = e^(-0.75) ≈ 0.4724
        decay_2021 = ImpactScorer.calculate_recency_decay(
            start_year=2019, end_year=2021, reference_year=2026, lambda_decay=0.15
        )
        expected_2021 = math.exp(-0.15 * 5)
        self.assertAlmostEqual(decay_2021, expected_2021, places=2)
        self.assertTrue(0.46 <= decay_2021 <= 0.48)

    def test_older_work_2016(self):
        # delta_t = 10 -> e^(-0.15 * 10) = e^(-1.5) ≈ 0.2231
        decay_2016 = ImpactScorer.calculate_recency_decay(
            start_year=2014, end_year=2016, reference_year=2026, lambda_decay=0.15
        )
        expected_2016 = math.exp(-0.15 * 10)
        self.assertAlmostEqual(decay_2016, expected_2016, places=2)
        self.assertTrue(0.21 <= decay_2016 <= 0.23)

    def test_present_and_none_end_year(self):
        decay_present = ImpactScorer.calculate_recency_decay(
            start_year=2024, end_year="Present", reference_year=2026
        )
        self.assertAlmostEqual(decay_present, 1.0, places=2)

        decay_none = ImpactScorer.calculate_recency_decay(
            start_year=2024, end_year=None, reference_year=2026
        )
        self.assertAlmostEqual(decay_none, 1.0, places=2)


class TestImpactScorerBulletScoring(unittest.TestCase):
    """Test full score_bullet calculation and ScoreBreakdown model."""

    def test_score_bullet_tier1_with_metrics_recent(self):
        bullet = "Architected high-throughput data pipelines improving performance by 70% and saving $1.2M."
        breakdown = ImpactScorer.score_bullet(
            bullet=bullet,
            start_year=2025,
            end_year=2026,
            duration_years=1.0,
            reference_year=2026,
            lambda_decay=0.15,
        )

        self.assertIsInstance(breakdown, ScoreBreakdown)
        self.assertAlmostEqual(breakdown.verb_score, 1.0, places=2)
        self.assertAlmostEqual(breakdown.metric_bonus, 0.2, places=2)
        # impact_score is capped at 1.0: min(1.0, 1.0 + 0.2) = 1.0
        self.assertAlmostEqual(breakdown.impact_score, 1.0, places=2)
        self.assertAlmostEqual(breakdown.recency_score, 1.0, places=2)
        # Final score = 0.25 * 1.0 + 0.35 * 1.0 + 0.40 * 1.0 = 1.0
        self.assertAlmostEqual(breakdown.final_score, 1.0, places=2)

    def test_score_bullet_tier2_with_metrics_2021(self):
        bullet = "Implemented automated ETL pipeline reducing latency to 50ms for 10k users."
        breakdown = ImpactScorer.score_bullet(
            bullet=bullet,
            start_year=2020,
            end_year=2021,
            duration_years=1.0,
            reference_year=2026,
            lambda_decay=0.15,
        )

        self.assertAlmostEqual(breakdown.verb_score, 0.7, places=2)
        self.assertAlmostEqual(breakdown.metric_bonus, 0.2, places=2)
        # impact_score = 0.7 + 0.2 = 0.9
        self.assertAlmostEqual(breakdown.impact_score, 0.9, places=2)
        # recency_score = e^(-0.15 * 5) ≈ 0.4724
        expected_recency = math.exp(-0.15 * 5)
        self.assertAlmostEqual(breakdown.recency_score, expected_recency, places=2)

        # Final score = 0.25 * duration (1.0) + 0.35 * recency (0.4724) + 0.40 * impact (0.90)
        # = 0.25 + 0.16533 + 0.36 = 0.77533
        expected_final = 0.25 * 1.0 + 0.35 * expected_recency + 0.40 * 0.90
        self.assertAlmostEqual(breakdown.final_score, expected_final, places=2)

    def test_score_bullet_custom_weights(self):
        bullet = "Optimized database caching layer."
        breakdown = ImpactScorer.score_bullet(
            bullet=bullet,
            start_year=2024,
            end_year=2025,
            duration_years=1.0,
            alpha=0.20,
            beta=0.30,
            gamma=0.50,
            reference_year=2026,
        )
        recency = math.exp(-0.15 * 1)
        expected_final = 0.20 * 1.0 + 0.30 * recency + 0.50 * 0.7
        self.assertAlmostEqual(breakdown.final_score, expected_final, places=2)


if __name__ == "__main__":
    unittest.main()
