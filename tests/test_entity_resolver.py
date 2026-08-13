"""Unit tests for src/postprocessing/entity_resolver.EntityResolver.

All tests use in-memory fixtures and do NOT require GraphRAG indexing or any
external service (pandas, sentence_transformers, LanceDB …).

SequenceMatcher ratio reference (lowercased strings):
    kuberntes / kubernetes      = 0.947
    python / "  python  "       = 0.750
    prasad rane / prasad        = 0.706
    amazon dynamodb / dynamodb  = 0.696
    senior engineer / staff eng = 0.690
    techone / technology one    = 0.667
    foo bar / foo               = 0.600
    aws / aws cloud             = 0.500
    azure / microsoft azure     = 0.500
    k8s / kubernetes            = 0.308
    aws / amazon web services   = 0.273
    aws lambda / aws ec2        = 0.471
    john smith / john a smith   = 0.909
"""

from __future__ import annotations

import math
import sys
import unittest
from unittest.mock import MagicMock

from unittest.mock import patch

from src.postprocessing.entity_resolver import (
    EntityResolver,
    ResolutionPair,
    create_entity_resolver_with_embeddings,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_mock_embed(vectors: dict[str, list[float]]):
    """Create an embed_fn returning pre-defined normalized vectors for texts."""
    cache: dict[str, list[float]] = {}
    def embed_fn(text, model_name):
        key = text.lower()
        vec = vectors.get(key, None)
        if vec is not None and key not in cache:
            norm = math.sqrt(sum(x * x for x in vec))
            cache[key] = [x / norm for x in vec] if norm else [0.0] * len(vec)
        return cache.get(key)
    return embed_fn


# ── String Similarity Tests ───────────────────────────────────────────────────

class TestStringSimilarityMerges(unittest.TestCase):
    """Tests for string-based deduplication with realistic name overlaps."""

    def test_typo_merged(self):
        """Minor typo merged into first-found canonical form."""
        ents = [{"name": "Kuberntes", "type": "Technology"},
                {"name": "Kubernetes",  "type": "Technology"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, pairs = resolver.resolve(ents)
        # Merged into single entry; canonical is first-found ("Kuberntes")
        self.assertEqual(len(resolved), 1)
        self.assertIn("Kuberntes", {r["name"] for r in resolved})
        self.assertNotIn("Kubernetes", {r["name"] for r in resolved})
        self.assertGreater(len(pairs), 0)
        # Canonical map points variant → lead
        self.assertEqual(resolver._canonical_map.get("Kubernetes"), "Kuberntes")

    def test_whitespace_dupe_merged(self):
        """Extra whitespace normalized to clean name."""
        ents = [{"name": "  Python  ",  "type": "Technology"},
                {"name": "Python",      "type": "Technology"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, pairs = resolver.resolve(ents)
        self.assertEqual(len(resolved), 1)
        self.assertIn("  Python  ", {r["name"] for r in resolved})
        self.assertNotIn("Python", {r["name"] for r in resolved})
        self.assertEqual(resolver._canonical_map.get("Python"), "  Python  ")

    def test_person_partial_merge(self):
        """'Prasad Rane' / 'Prasad' share prefix (ratio 0.706 > 0.55)."""
        ents = [{"name": "Prasad Rane", "type": "Person"},
                {"name": "Prasad",    "type": "Person"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, pairs = resolver.resolve(ents)
        self.assertEqual(len(resolved), 1)
        self.assertNotIn("Prasad", {r["name"] for r in resolved})
        self.assertGreater(len(pairs), 0)

    def test_common_prefix_merge(self):
        """'Amazon DynamoDB' / 'DynamoDB' share long prefix (ratio 0.696)."""
        ents = [{"name": "Amazon DynamoDB", "type": "Technology"},
                {"name": "DynamoDB",        "type": "Technology"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, _ = resolver.resolve(ents)
        self.assertEqual(len(resolved), 1)

    def test_role_merge(self):
        """'Senior Engineer' / 'Staff Engineer' overlap (ratio 0.690)."""
        ents = [{"name": "Senior Engineer", "type": "Role"},
                {"name": "Staff Engineer",  "type": "Role"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, _ = resolver.resolve(ents)
        self.assertEqual(len(resolved), 1)

    def test_aws_not_merged_at_055(self):
        """'AWS' / 'amazon web services' ratio 0.273 < 0.55 — stays separate."""
        ents = [{"name": "AWS",           "type": "Technology"},
                {"name": "Amazon Web Services", "type": "Technology"},
                {"name": "Python",          "type": "Technology"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, pairs = resolver.resolve(ents)
        names = {r["name"] for r in resolved}
        self.assertEqual(len(names), 3)
        self.assertEqual(len(pairs), 0)

    def test_azure_not_merged_at_055(self):
        """'Azure' / 'Microsoft Azure' ratio 0.500 < 0.55 — stays separate."""
        ents = [{"name": "Azure",         "type": "Technology"},
                {"name": "Microsoft Azure","type": "Technology"}]
        resolver = EntityResolver(string_threshold=0.55)
        resolved, _ = resolver.resolve(ents)
        names = {r["name"] for r in resolved}
        self.assertEqual(len(names), 2)


class TestDistinctEntitySafety(unittest.TestCase):
    """Verify truly distinct entities NEVER merge at default threshold (0.85)."""

    def setUp(self):
        self.resolver = EntityResolver()  # string_threshold=0.85

    def test_aws_services_stay_separate(self):
        """AWS Lambda / EC2 / S3 are distinct products."""
        resolved, _ = self.resolver.resolve([
            {"name": "AWS Lambda",  "type": "Technology"},
            {"name": "AWS EC2",     "type": "Technology"},
            {"name": "AWS S3",      "type": "Technology"},
        ])
        names = {r["name"] for r in resolved}
        self.assertIn("AWS Lambda", names)
        self.assertIn("AWS EC2", names)
        self.assertIn("AWS S3", names)

    def test_different_techs_no_merge(self):
        """Completely different technologies stay separate."""
        resolved, _ = self.resolver.resolve([
            {"name": "Python",      "type": "Technology"},
            {"name": "Java",        "type": "Technology"},
            {"name": "TypeScript",  "type": "Technology"},
            {"name": "Go",          "type": "Technology"},
        ])
        self.assertEqual(len(resolved), 4)

    def test_different_types_never_merged(self):
        """Cross-type comparison is never attempted."""
        resolved, pairs = self.resolver.resolve([
            {"name": "Python",  "type": "Technology"},
            {"name": "Python",  "type": "Skill"},
        ])
        self.assertEqual(len(resolved), 2)
        self.assertEqual(len(pairs), 0)

    def test_full_set_preserves_distinct(self):
        """Default threshold on full realistic dataset preserves distinct entities."""
        ents = _build_full_entities()
        resolver = EntityResolver()
        resolved, pairs = resolver.resolve(ents)
        names = {r["name"] for r in resolved}
        # No merges happen at 0.85 threshold — all 19 entities survive
        self.assertEqual(len(names), 19)
        for expected in ["AWS Lambda", "AWS EC2", "AWS S3", "Python", "Java",
                         "DynamoDB", "Prasad Rane", "Senior Engineer", "AWS Cloud"]:
            self.assertIn(expected, names)


class TestThresholdTuning(unittest.TestCase):
    """Configurable thresholds control merge aggressiveness."""

    def test_higher_threshold_fewer_merges(self):
        """Stricter threshold → fewer merges → more final entities."""
        strict = EntityResolver(string_threshold=0.85)
        relaxed = EntityResolver(string_threshold=0.55)
        ents = _build_full_entities()

        _, p_strict = strict.resolve(ents)
        _, p_relaxed = relaxed.resolve(ents)

        self.assertLess(len(p_strict), len(p_relaxed))

    def test_custom_threshold_attribute(self):
        r = EntityResolver(string_threshold=0.77, semantic_threshold=0.63)
        self.assertEqual(r.string_threshold, 0.77)
        self.assertEqual(r.semantic_threshold, 0.63)

    def test_zero_threshold_merges_all_same_type(self):
        """At zero threshold everything in same type bucket merges."""
        resolver = EntityResolver(string_threshold=0.0)
        resolved, _ = resolver.resolve([
            {"name": "Alpha",  "type": "Technology"},
            {"name": "Beta",   "type": "Technology"},
            {"name": "Gamma",  "type": "Technology"},
        ])
        self.assertEqual(len(resolved), 1)


# ── Semantic Similarity Tests ─────────────────────────────────────────────────

class TestSemanticSimilarity(unittest.TestCase):
    """Embedding-aware resolution with mocked vectors.

    The AND gate requires BOTH string sim >= string_threshold AND semantic sim >=
    semantic_threshold for semantic types (Technology/Skill/Competency). Non-semantic
    types skip the embedding check entirely.
    """

    def _vec(self, val=1.0, n=16):
        """Uniform vector."""
        return [val] * n

    def test_semantic_boost_on_technology(self):
        """High embedding sim bridges gap where string sim is moderate."""
        # Need string_sim >= 0.85 AND semantic_sim >= 0.80
        # "TermOne" / "Term One" have good string overlap (~0.87)
        v1 = self._vec(1.0)
        v2 = self._vec(0.95) + [0.5] * 4  # slightly different in some dims
        fn = _make_mock_embed({"termone": v1, "term one": v2})
        resolver = EntityResolver(string_threshold=0.80, semantic_threshold=0.80, embed_fn=fn)

        resolved, pairs = resolver.resolve([
            {"name": "TermOne",   "type": "Technology"},
            {"name": "Term One",  "type": "Technology"},
            {"name": "Python",    "type": "Technology"},
        ])
        names = {r["name"] for r in resolved}
        self.assertIn("TermOne", names)
        self.assertNotIn("Term One", names)
        self.assertIn("Python", names)
        self.assertEqual(len(pairs), 1)
        self.assertIsNotNone(pairs[0].semantic_score)
        self.assertGreater(pairs[0].semantic_score, 0.5)

    def test_skills_use_semantic(self):
        """Skill type also benefits from embedding boost."""
        v_k8s   = self._vec(1.0)
        v_kub   = self._vec(0.95) + [0.5] * 4
        fn = _make_mock_embed({"k8s": v_k8s, "kubernetes": v_kub})
        # String sim(k8s,kubernetes)=0.308 → use low threshold so AND gate passes
        resolver = EntityResolver(string_threshold=0.25, semantic_threshold=0.80, embed_fn=fn)

        res, pairs = resolver.resolve([
            {"name": "k8s",         "type": "Skill"},
            {"name": "Kubernetes",  "type": "Skill"},
        ])
        names = {r["name"] for r in res}
        self.assertIn("k8s", names)  # First found is canonical
        self.assertNotIn("Kubernetes", names)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].type_, "Skill")

    def test_embedding_unavailable_falls_back(self):
        """When embed_fn returns None, resolution works via string alone."""
        always_none = MagicMock(return_value=None)
        resolver = EntityResolver(string_threshold=0.45, embed_fn=always_none)

        resolved, pairs = resolver.resolve([
            {"name": "AWS",                  "type": "Technology"},
            {"name": "Amazon Web Services",  "type": "Technology"},
        ])
        self.assertEqual(len(resolved), 2)
        self.assertEqual(len(pairs), 0)

    def test_and_gate_both_thresholds_required(self):
        """Both string AND semantic must individually pass for semantic types."""
        v_good_em = self._vec(1.0)
        v_bad_str = [0.3] + self._vec(1.0)[1:]
        fn = _make_mock_embed({"term1": v_good_em, "completely different term": v_bad_str})
        resolver = EntityResolver(string_threshold=0.85, semantic_threshold=0.80, embed_fn=fn)

        resolved, _ = resolver.resolve([
            {"name": "Term1",                    "type": "Technology"},
            {"name": "Completely Different Term", "type": "Technology"},
        ])
        # String sim ≈ 0.21 < 0.85 → AND gate blocks merge despite good embedding sim
        self.assertEqual(len(resolved), 2)

    def test_non_semantic_type_ignores_embeddings(self):
        """Person types skip semantic check — pure string similarity only."""
        fake_fn = MagicMock()
        resolver = EntityResolver(string_threshold=0.55, embed_fn=fake_fn)
        resolved, pairs = resolver.resolve([
            {"name": "John Smith",      "type": "Person"},
            {"name": "John A Smith",    "type": "Person"},
        ])
        fake_fn.assert_not_called()  # semantic check skipped for Person
        # SequenceMatcher('john smith', 'john a smith') = 0.909 > 0.55 → merge
        self.assertEqual(len(resolved), 1)
        self.assertGreater(len(pairs), 0)


# ── Relationship Update Tests ─────────────────────────────────────────────────

class TestRelationshipUpdates(unittest.TestCase):
    """Verify relationship relabeling after entity merging.

    NOTE: update_relationships replaces MERGED VARIANT names with canonical names.
    Edges already using the canonical name are unaffected (they're already correct).
    """

    def setUp(self):
        self.resolver = EntityResolver(string_threshold=0.55)

    def test_variant_edges_relabel_to_canonical(self):
        """Edges referencing merged variants get relabeled."""
        ents = [{"name": "Prasad Rane", "type": "Person"},
                {"name": "Prasad",    "type": "Person"}]
        rels = [{"source": "Prasad",     "target": "Other", "description": "edge"},
                {"source": "Prasad Rane", "target": "Other", "description": "edge2"}]

        self.resolver.resolve(ents)
        updated, relabeled = self.resolver.update_relationships(rels)

        sources = {r["source"] for r in updated}
        # "Prasad" (variant) → replaced by canonical "Prasad Rane"
        self.assertNotIn("Prasad", sources)
        self.assertIn("Prasad Rane", sources)
        self.assertGreater(len(relabeled), 0)

    def test_no_merges_means_no_relabels(self):
        """No entity merges → no relationship relabeling."""
        resolver = EntityResolver(string_threshold=1.0)
        resolver.resolve([{"name": "UniqueThing", "type": "Technology"}])
        updated, relabeled = resolver.update_relationships([
            {"source": "UniqueThing", "target": "Other", "description": "x"},
        ])
        self.assertEqual(relabeled, [])
        self.assertEqual(updated[0]["source"], "UniqueThing")

    def test_both_sides_relabel(self):
        """Both source AND target sides can be relabeled."""
        ents = [{"name": "Prasad Rane", "type": "Person"},
                {"name": "Prasad",    "type": "Person"},
                {"name": "Senior Engineer", "type": "Role"},
                {"name": "Staff Engineer",  "type": "Role"}]
        rels = [{"source": "Prasad",  "target": "Staff Engineer", "description": "a"},
                {"source": "John",    "target": "Other",            "description": "b"}]

        self.resolver.resolve(ents)
        updated, _ = self.resolver.update_relationships(rels)

        # "Prasad" → "Prasad Rane"; "Staff Engineer" → "Senior Engineer"
        self.assertEqual(updated[0]["source"], "Prasad Rane")
        self.assertEqual(updated[0]["target"], "Senior Engineer")
        # Unrelated names unchanged
        self.assertEqual(updated[1]["source"], "John")
        self.assertEqual(updated[1]["target"], "Other")

    def test_unknown_names_pass_through(self):
        """Names not in canonical_map are left untouched."""
        resolver = EntityResolver(string_threshold=1.0)
        resolver.resolve([{"name": "A", "type": "Technology"}])
        updated, _ = resolver.update_relationships([
            {"source": "B", "target": "C", "description": "unknown"},
        ])
        self.assertEqual(updated[0]["source"], "B")
        self.assertEqual(updated[0]["target"], "C")

    def test_relabeled_audit_trail(self):
        """Audit trail records each relabeling change."""
        ents = [{"name": "Prasad Rane", "type": "Person"},
                {"name": "Prasad",    "type": "Person"}]
        rels = [{"source": "Prasad",     "target": "X", "description": "a"},
                {"source": "Y",          "target": "Z", "description": "b"}]

        self.resolver.resolve(ents)
        _, relabeled = self.resolver.update_relationships(rels)

        self.assertGreater(len(relabeled), 0)
        for entry in relabeled:
            self.assertEqual(len(entry), 3)


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEmptyAndEdgeCases(unittest.TestCase):
    """Boundary conditions and error-free operation."""

    def test_empty_input(self):
        resolver = EntityResolver()
        resolved, pairs = resolver.resolve([])
        self.assertEqual(resolved, [])
        self.assertEqual(pairs, [])

    def test_single_entity(self):
        resolver = EntityResolver()
        resolved, pairs = resolver.resolve([{"name": "Solo", "type": "Technology"}])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["name"], "Solo")
        self.assertEqual(pairs, [])

    def test_attributes_absorbed_on_merge(self):
        """Attributes from merged variants accumulate into canonical row."""
        ents = [{"name": "PythonLib", "type": "Technology", "description": "short"},
                {"name": "PythonLibrary", "type": "Technology", "description": "a much longer detailed description here"}]
        resolver = EntityResolver(string_threshold=0.45)
        resolved, _ = resolver.resolve(ents)
        self.assertEqual(len(resolved), 1)
        # Longer description should have been absorbed into the canonical row
        self.assertEqual(resolved[0]["description"],
                         "a much longer detailed description here")
        # Verify merge happened — _merged_from contains at least one entry
        self.assertGreater(len(resolved[0].get("_merged_from", [])), 0)

    def test_resolution_pair_dataclass(self):
        pair = ResolutionPair(canonical="AWS", merged_into="Amazon Web Services",
                              string_score=0.27, semantic_score=0.88, type_="Technology")
        self.assertEqual(pair.canonical, "AWS")
        self.assertEqual(pair.merged_into, "Amazon Web Services")
        self.assertEqual(pair.string_score, 0.27)
        self.assertEqual(pair.semantic_score, 0.88)
        self.assertEqual(pair.type_, "Technology")


# ── Factory Function Tests ────────────────────────────────────────────────────

class TestFactoryFunction(unittest.TestCase):
    """Test create_entity_resolver_with_embeddings()."""

    def test_factory_without_sentence_transformers(self):
        """Absent sentence_transformers → string-only resolver."""
        saved = sys.modules.pop("sentence_transformers", None)
        try:
            with patch("builtins.__import__", side_effect=ImportError):
                resolver = create_entity_resolver_with_embeddings()
                self.assertIsInstance(resolver, EntityResolver)
                self.assertIsNone(resolver._embed_fn)
        finally:
            if saved is not None:
                sys.modules["sentence_transformers"] = saved

    def test_factory_with_mocked_transformers(self):
        """Present sentence_transformers → embed_fn configured."""
        mock_arr = MagicMock()
        mock_arr.tolist.return_value = [0.5] * 16
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = mock_arr
        mock_st = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_encoder

        saved = sys.modules.pop("sentence_transformers", None)
        try:
            with patch.dict(sys.modules, {"sentence_transformers": mock_st}):
                resolver = create_entity_resolver_with_embeddings()
                self.assertIsNotNone(resolver._embed_fn)
                result = resolver._embed_fn("test", "dummy-model")
                self.assertIsNotNone(result)
                self.assertEqual(len(result), 16)
        finally:
            if saved is not None:
                sys.modules["sentence_transformers"] = saved

    def test_factory_custom_params(self):
        """Custom thresholds forwarded correctly."""
        mock_arr = MagicMock()
        mock_arr.tolist.return_value = [0.5] * 16
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = mock_arr
        mock_st = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_encoder

        saved = sys.modules.pop("sentence_transformers", None)
        try:
            with patch.dict(sys.modules, {"sentence_transformers": mock_st}):
                resolver = create_entity_resolver_with_embeddings(
                    string_threshold=0.90, semantic_threshold=0.85)
                self.assertEqual(resolver.string_threshold, 0.90)
                self.assertEqual(resolver.semantic_threshold, 0.85)
        finally:
            if saved is not None:
                sys.modules["sentence_transformers"] = saved


# ── Helper Fixture Builders ───────────────────────────────────────────────────

def _build_full_entities():
    """Full realistic entity set used by several tests."""
    return [
        {"name": "AWS",               "type": "Technology"},
        {"name": "Amazon Web Services", "type": "Technology"},
        {"name": "AWS Cloud",         "type": "Technology"},
        {"name": "Azure",             "type": "Technology"},
        {"name": "Microsoft Azure",   "type": "Technology"},
        {"name": "AWS Lambda",        "type": "Technology"},
        {"name": "AWS EC2",           "type": "Technology"},
        {"name": "AWS S3",            "type": "Technology"},
        {"name": "DynamoDB",          "type": "Technology"},
        {"name": "Amazon DynamoDB",   "type": "Technology"},
        {"name": "Python",            "type": "Technology"},
        {"name": "Java",              "type": "Technology"},
        {"name": "Prasad Rane",       "type": "Person"},
        {"name": "Prasad",            "type": "Person"},
        {"name": "Senior Engineer",   "type": "Role"},
        {"name": "Staff Engineer",    "type": "Role"},
        {"name": "k8s",               "type": "Skill"},
        {"name": "Kubernetes",        "type": "Skill"},
        {"name": "Terraform",         "type": "Skill"},
    ]


if __name__ == "__main__":
    unittest.main()
