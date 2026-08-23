"""Tests for GraphRAGEngine — real parquet artifacts from GraphRAG index."""

import asyncio
import concurrent.futures
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# Ensure project root is importable.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy

from src.query.graphrag_engine import GraphRAGEngine, reset_engine, get_engine, _tid_match


_ROOT = str(Path(__file__).resolve().parent.parent)

_LANCEDB_DIR = Path(_ROOT) / "output" / "lancedb"
_ENTITIES_PARQUET = Path(_ROOT) / "output" / "entities.parquet"
_HAS_ARTIFACTS = _LANCEDB_DIR.exists() and _ENTITIES_PARQUET.exists()
_SKIP_NO_ARTIFACTS = "GraphRAG artifacts not found (run `graphrag index` first)"


def _sync_run(coro):
    """Run an async coroutine in an isolated thread to prevent event loop collision with pytest-playwright."""
    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_worker).result()


# ── initialisation ──────────────────────────────────────────────────────────

class TestGraphRAGEngineInit(unittest.TestCase):

    def setUp(self):
        reset_engine()

    def test_init_default_root_dir(self):
        engine = GraphRAGEngine()
        self.assertEqual(engine.root_dir, Path(_ROOT))
        self.assertFalse(engine.connected)

    def test_init_custom_root_dir(self):
        rd = Path("/tmp/fake")
        engine = GraphRAGEngine(rd)
        self.assertEqual(engine.root_dir, rd)

    def test_connect_raises_on_missing_lancedb(self):
        with TemporaryDirectory() as td:
            engine = GraphRAGEngine(td)
            with self.assertRaisesRegex(FileNotFoundError, "LanceDB"):
                _sync_run(engine.connect())

    def test_connect_raises_on_missing_parquet(self):
        with TemporaryDirectory() as td:
            lancedb_dir = Path(td) / "output" / "lancedb"
            lancedb_dir.mkdir(parents=True)
            engine = GraphRAGEngine(td)
            with self.assertRaisesRegex(
                FileNotFoundError, "Missing GraphRAG artefact"
            ):
                _sync_run(engine.connect())

    @unittest.skipUnless(_HAS_ARTIFACTS, _SKIP_NO_ARTIFACTS)
    def test_connect_success(self):
        engine = _sync_run(GraphRAGEngine(_ROOT).connect())
        self.assertTrue(engine.connected)
        self.assertIsNotNone(engine._entities)
        self.assertIsNotNone(engine._communities)
        self.assertGreater(len(engine._entities), 0)
        self.assertGreater(len(engine._communities), 0)

    def test_disconnect(self):
        engine = GraphRAGEngine(_ROOT)
        engine._db = object()
        engine._entities = object()
        self.assertTrue(engine.connected)
        engine._db = None
        self.assertFalse(engine.connected)


# ── retrieval modes (mocked get_embedding — no API keys needed in tests) ────

@unittest.skipUnless(_HAS_ARTIFACTS, _SKIP_NO_ARTIFACTS)
class TestRetrievalModes(unittest.TestCase):

    def setUp(self):
        reset_engine()

    # The LanceDB default-text_unit-text table uses 2048-dim vectors.
    MOCK_EMB_2K = [0.1] * 2048

    @patch.object(GraphRAGEngine, 'get_embedding', return_value=MOCK_EMB_2K)
    def test_local_retrieval_returns_dict_keys(self, mock_emb):
        engine = _sync_run(GraphRAGEngine(_ROOT).connect())
        result = _sync_run(engine._local_retrieval("AWS cloud computing"))
        self.assertIsInstance(result, dict)
        self.assertIn("text_units", result)
        self.assertIn("entities", result)
        self.assertIn("relationships", result)
        self.assertGreater(len(result["text_units"]), 0)

    @patch.object(GraphRAGEngine, 'get_embedding', return_value=MOCK_EMB_2K)
    def test_global_retrieval_queries_community_table(self, mock_emb):
        engine = _sync_run(GraphRAGEngine(_ROOT).connect())
        result = _sync_run(engine._global_retrieval("career summary executive"))
        self.assertIn("communities", result)
        self.assertGreater(len(result["communities"]), 0)

    @patch.object(GraphRAGEngine, 'get_embedding', return_value=MOCK_EMB_2K)
    def test_drift_expands_context(self, mock_emb):
        engine = _sync_run(GraphRAGEngine(_ROOT).connect())
        result = _sync_run(engine._drift_retrieval("Python microservices cloud"))
        self.assertGreaterEqual(set(result.keys()), {"text_units", "entities", "relationships"})
        self.assertGreater(len(result["entities"]), 0)

    @patch.object(GraphRAGEngine, 'get_embedding', return_value=MOCK_EMB_2K)
    def test_hybrid_local_retrieval(self, mock_emb):
        engine = _sync_run(GraphRAGEngine(_ROOT).connect())
        result = _sync_run(engine._local_retrieval("AWS Terraform Kubernetes", top_k=10))
        self.assertIn("text_units", result)
        self.assertFalse(result["text_units"].empty)


# ── mocked retrieval logic (unconditional unit tests) ──────────────────────

class TestMockedRetrieval(unittest.TestCase):

    def setUp(self):
        reset_engine()

    def test_drift_prunes_low_weight_edges(self):
        engine = GraphRAGEngine(_ROOT)
        engine._entities = pd.DataFrame([
            {"id": "e1", "title": "Prasad Rane", "type": "Person", "description": "Candidate", "text_unit_ids": ["t1"]},
            {"id": "e2", "title": "Kubernetes", "type": "Technology", "description": "K8s platform", "text_unit_ids": ["t1"]},
            {"id": "e3", "title": "ObsoleteTool", "type": "Technology", "description": "Old tool", "text_unit_ids": ["t1"]},
        ])
        engine._relationships = pd.DataFrame([
            {"id": "r1", "source": "e1", "target": "e2", "description": "Expert in", "weight": 9.0},
            {"id": "r2", "source": "e1", "target": "e3", "description": "Mentioned once", "weight": 0.1},
        ])
        engine._text_units = pd.DataFrame([
            {"id": "t1", "text": "Prasad Rane has deep experience with Kubernetes."}
        ])

        async def fake_local(query, top_k=10):
            return {
                "text_units": engine._text_units,
                "entities": engine._entities[engine._entities["id"] == "e1"],
                "relationships": engine._relationships,
            }

        engine._local_retrieval = fake_local  # type: ignore
        result = _sync_run(engine._drift_retrieval("Kubernetes", min_edge_weight=0.5))
        
        ent_ids = result["entities"]["id"].tolist()
        self.assertIn("e2", ent_ids)
        self.assertNotIn("e3", ent_ids, "Low-weight edge (<0.5) should be pruned in DRIFT mode")

    def test_unknown_mode_raises(self):
        engine = GraphRAGEngine(_ROOT)
        with self.assertRaisesRegex(ValueError, "Unknown GraphRAG mode"):
            _sync_run(engine.retrieve("query", mode="bogus"))

    def test_local_retrieval_with_bm25_fallback(self):
        engine = GraphRAGEngine(_ROOT)
        engine._text_units = pd.DataFrame([
            {"id": "t1", "text": "Architected AWS EKS clusters and Kafka pipelines."},
            {"id": "t2", "text": "Led agile team meetings and stakeholder communication."}
        ])
        engine._entities = pd.DataFrame([
            {"id": "e1", "title": "Kafka", "type": "Technology", "description": "Streaming", "text_unit_ids": ["t1"]}
        ])
        engine._relationships = pd.DataFrame([
            {"id": "r1", "source": "e1", "target": "e1", "description": "self", "weight": 1.0}
        ])
        result = _sync_run(engine._local_retrieval("Kafka", top_k=2))
        self.assertIn("text_units", result)
        self.assertFalse(result["text_units"].empty)
        self.assertEqual(result["text_units"].iloc[0]["id"], "t1")
        self.assertIn("e1", result["entities"]["id"].tolist())


# ── prompt formatting helpers ───────────────────────────────────────────────

class TestFormatContext(unittest.TestCase):

    def setUp(self):
        reset_engine()

    def test_empty_context_returns_blank(self):
        self.assertEqual(GraphRAGEngine.format_context({}), "")

    def test_text_units_section(self):
        ctx = {
            "text_units": pd.DataFrame([{"id": "t1", "text": "Prasad worked at ABC Corp"}]),
            "entities": pd.DataFrame(),
            "relationships": pd.DataFrame(),
            "communities": pd.DataFrame(),
        }
        rendered = GraphRAGEngine.format_context(ctx)
        self.assertIn("## Relevant Text Segments", rendered)
        self.assertIn("ABC Corp", rendered)

    def test_entities_section(self):
        ctx = {
            "text_units": pd.DataFrame(),
            "entities": pd.DataFrame([{"id": "e1", "title": "AWS", "type": "Technology", "description": "Cloud platform"}]),
            "relationships": pd.DataFrame(),
            "communities": pd.DataFrame(),
        }
        rendered = GraphRAGEngine.format_context(ctx)
        self.assertIn("**AWS**", rendered)
        self.assertIn("Cloud platform", rendered)

    def test_relationships_section(self):
        ctx = {
            "text_units": pd.DataFrame(),
            "entities": pd.DataFrame(),
            "relationships": pd.DataFrame([{"id": "r1", "source": "Alice", "target": "Bob", "description": "managed by"}]),
            "communities": pd.DataFrame(),
        }
        rendered = GraphRAGEngine.format_context(ctx)
        self.assertIn("## Knowledge Graph Triples", rendered)
        self.assertIn("**Alice**:", rendered)
        self.assertIn("--[managed by]--> **Bob**", rendered)


# ── source extraction ───────────────────────────────────────────────────────

class TestExtractSources(unittest.TestCase):

    def setUp(self):
        reset_engine()

    def test_extract_nothing(self):
        self.assertEqual(GraphRAGEngine.extract_sources({"entities": pd.DataFrame()}), [])

    def test_extract_entity_sources(self):
        ctx = {
            "entities": pd.DataFrame([{"id": "e1", "name": "AWS", "description": "Amazon Web Services"}]),
            "communities": pd.DataFrame(),
        }
        sources = GraphRAGEngine.extract_sources(ctx)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["type"], "entity")
        self.assertEqual(sources[0]["name"], "AWS")


# ── tiny utility ────────────────────────────────────────────────────────────

class TestTidMatch(unittest.TestCase):

    def test_string_tid_in_list(self):
        self.assertTrue(_tid_match("abc", ["abc", "def"]))
        self.assertFalse(_tid_match("xyz", ["abc", "def"]))

    def test_none_arr_false(self):
        self.assertFalse(_tid_match("abc", None))

    def test_string_arr_handled(self):
        self.assertTrue(_tid_match("abc", "abc"))
        self.assertFalse(_tid_match("abc", "def"))

    def test_ndarray_handling(self):
        arr = numpy.array(["abc", "def"])
        self.assertTrue(_tid_match("abc", arr))
        self.assertFalse(_tid_match("xyz", arr))


# ── retrieve_healed self-healing guardrail test ──────────────────────────────

class TestRetrieveHealed(unittest.TestCase):

    def setUp(self):
        reset_engine()

    def test_retrieve_healed_sufficient_returns_no_trace(self):
        engine = GraphRAGEngine(Path(_ROOT))
        
        rich_ctx = {
            "text_units": pd.DataFrame([
                {
                    "id": "t1",
                    "text": (
                        "Prasad architected AWS ECS Fargate microservices with Python and FastAPI, "
                        "reducing infrastructure cost by 40% and achieving 99.95% uptime across "
                        "cloud production environments with automated deployment pipelines and CloudWatch."
                    ),
                }
            ]),
            "entities": pd.DataFrame([{"id": "e1", "title": "AWS", "description": "Cloud"}]),
            "relationships": pd.DataFrame(),
            "communities": pd.DataFrame(),
        }
        
        async def fake_retrieve(query, mode="local", top_k=10):
            return rich_ctx

        engine.retrieve = fake_retrieve  # type: ignore

        ctx, trace = _sync_run(engine.retrieve_healed("What AWS experience does Prasad have?", mode="local"))
        self.assertEqual(ctx, rich_ctx)
        self.assertEqual(trace, [])

    def test_retrieve_healed_escalates_on_empty_context(self):
        engine = GraphRAGEngine(Path(_ROOT))
        
        empty_ctx = {
            "text_units": pd.DataFrame(),
            "entities": pd.DataFrame(),
            "relationships": pd.DataFrame(),
            "communities": pd.DataFrame(),
        }
        rich_ctx = {
            "text_units": pd.DataFrame([{"id": "t1", "text": "Prasad worked with Kafka event streaming and microservices."}]),
            "entities": pd.DataFrame([{"id": "e1", "title": "Kafka", "description": "Streaming"}]),
            "relationships": pd.DataFrame(),
            "communities": pd.DataFrame(),
        }

        async def fake_retrieve(query, mode="local", top_k=10):
            if mode == "local":
                return empty_ctx
            return rich_ctx

        engine.retrieve = fake_retrieve  # type: ignore

        ctx, trace = _sync_run(engine.retrieve_healed("Tell me about Kafka experience", mode="local"))
        self.assertEqual(ctx, rich_ctx)
        self.assertGreater(len(trace), 0)


# ── singleton helper ────────────────────────────────────────────────────────

@unittest.skipUnless(_HAS_ARTIFACTS, _SKIP_NO_ARTIFACTS)
class TestGetEngine(unittest.TestCase):

    def test_get_engine_caches(self):
        reset_engine()
        e1 = _sync_run(get_engine(Path(_ROOT)))
        e2 = _sync_run(get_engine(Path(_ROOT)))
        self.assertIs(e1, e2)

    def test_reset_clears_singleton(self):
        reset_engine()
        e1 = _sync_run(get_engine(Path(_ROOT)))
        reset_engine()
        e2 = _sync_run(get_engine(Path(_ROOT)))
        self.assertIsNot(e1, e2)


if __name__ == "__main__":
    unittest.main()
