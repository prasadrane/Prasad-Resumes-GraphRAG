"""Unit + integration tests for src.shared.graph_controller."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure repo root is on sys.path for `src.*` imports when run via unittest discovery
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestGraphControllerMissingFiles(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        self.mod = graph_controller
        self.mod.clear_graph_cache()

    def test_missing_parquet_raises(self):
        """When a parquet is absent, get_explorer_payload raises GraphNotBuiltError."""
        fake_path = Path("/nonexistent/entities.parquet")
        with patch.object(self.mod, "ENTITIES_PATH", fake_path):
            with patch.object(self.mod, "_PARQUET_PATHS", (fake_path,)):
                with self.assertRaises(self.mod.GraphNotBuiltError):
                    self.mod.get_explorer_payload()


LIVE_PARQUETS_EXIST = all(
    Path(f"output/{name}").exists()
    for name in ["entities.parquet", "relationships.parquet", "communities.parquet"]
)


@unittest.skipUnless(LIVE_PARQUETS_EXIST, "Requires live output/*.parquet")
class TestGraphControllerLive(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        self.mod = graph_controller
        self.mod.clear_graph_cache()

    def test_payload_shape_against_live_parquets(self):
        payload = self.mod.get_explorer_payload()
        self.assertIn("freshness", payload)
        self.assertIn("elements", payload)
        self.assertIn("nodes", payload["elements"])
        self.assertIn("edges", payload["elements"])
        self.assertGreater(payload["freshness"]["entity_count"], 0)
        self.assertGreater(payload["freshness"]["community_count"], 0)

    def test_cache_hit_on_second_call(self):
        first = self.mod.get_explorer_payload()
        second = self.mod.get_explorer_payload()
        self.assertIs(first, second)

    def test_node_ids_use_prefixes(self):
        payload = self.mod.get_explorer_payload()
        for n in payload["elements"]["nodes"]:
            self.assertTrue(
                n["data"]["id"].startswith("c:") or n["data"]["id"].startswith("e:"),
                f"Node ID missing prefix: {n['data']['id']}",
            )
        for e in payload["elements"]["edges"]:
            self.assertTrue(e["data"]["id"].startswith("r:"))
            self.assertTrue(e["data"]["source"].startswith("e:"))
            self.assertTrue(e["data"]["target"].startswith("e:"))

    def test_entities_parented_to_communities(self):
        payload = self.mod.get_explorer_payload()
        community_ids = {
            n["data"]["id"]
            for n in payload["elements"]["nodes"]
            if n["data"]["kind"] == "community"
        }
        for n in payload["elements"]["nodes"]:
            if n["data"]["kind"] == "entity":
                self.assertIn(
                    n["data"]["parent"], community_ids,
                    f"Entity {n['data']['id']} has unknown parent {n['data']['parent']}",
                )


@unittest.skipUnless(LIVE_PARQUETS_EXIST, "Requires live output/*.parquet")
class TestGraphEndpoint(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        graph_controller.clear_graph_cache()
        from fastapi import FastAPI
        from src.shared.api_routes import shared_router
        app = FastAPI()
        app.include_router(shared_router)
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_endpoint_returns_200_with_live_parquets(self):
        resp = self.client.get("/api/graph/explore")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("freshness", body)
        self.assertIn("elements", body)

    def test_endpoint_returns_503_when_parquets_missing(self):
        from src.shared import graph_controller
        from unittest.mock import patch
        fake = Path("/nonexistent/entities.parquet")
        with patch.object(graph_controller, "_PARQUET_PATHS", (fake,)):
            resp = self.client.get("/api/graph/explore")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["detail"]["code"], "GRAPH_NOT_BUILT")


if __name__ == "__main__":
    unittest.main()
