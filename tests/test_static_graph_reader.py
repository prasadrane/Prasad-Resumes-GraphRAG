"""
Unit tests for src/query/static_graph_reader.py.

All file I/O is redirected at temp directories by patching the module-level
OUTPUT_DIR_PATH / ROOT_DIR names the reader resolves at call time. Pytest-style
(uses tmp_path, monkeypatch, conftest fixtures); not collected by unittest.
"""

import json

import src.query.static_graph_reader as reader


def _patch_dirs(monkeypatch, out_dir, root_dir):
    monkeypatch.setattr(reader, "OUTPUT_DIR_PATH", out_dir)
    monkeypatch.setattr(reader, "ROOT_DIR", root_dir)


def test_reads_entities_from_json(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.read_precomputed_entities() == entities


def test_malformed_json_falls_back_to_master_resume(
    tmp_path, monkeypatch, sample_master_resume_text
):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    (out_dir / "graph_entities.json").write_text("{ not valid json", encoding="utf-8")
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "MASTER_RESUME.txt").write_text(sample_master_resume_text, encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    entities = reader.read_precomputed_entities()

    assert len(entities) == 4
    assert entities[0]["title"] == "Prasad Rane"
    assert "AWS ECS Fargate" in entities[2]["content"]


def test_no_artifacts_returns_empty_list(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.read_precomputed_entities() == []


def test_search_matches_case_insensitive(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS ECS Fargate services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["aws"])

    assert len(matched) == 1
    assert "Built AWS ECS Fargate services" in matched[0]


def test_search_caps_results_at_ten(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [
        {"title": f"Job {i}", "content": "python engineering work"} for i in range(12)
    ]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["python"])

    assert len(matched) == 10


def test_search_truncates_matches_to_300_chars(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Big", "content": "aws " + "x" * 500}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["aws"])

    assert len(matched) == 1
    assert len(matched[0]) == 300


def test_search_empty_keywords_returns_empty(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.search_static_graph([]) == []
