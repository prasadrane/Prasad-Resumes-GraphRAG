"""
test_settings_and_prompts.py — Unit tests for GraphRAG settings and domain prompts.
"""

from pathlib import Path
import yaml
import pytest

from src.config import ROOT_DIR


def test_settings_yaml_configuration():
    """Verify that settings.yaml has entity/community embeddings and gleanings enabled."""
    settings_file = ROOT_DIR / "config" / "settings.yaml"
    assert settings_file.exists(), f"Missing settings.yaml at {settings_file}"

    with open(settings_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg.get("embed_entities") is True, "embed_entities must be True for entity vector search"
    assert cfg.get("embed_communities") is True, "embed_communities must be True for community vector search"
    
    entity_extraction = cfg.get("entity_extraction", {})
    assert entity_extraction.get("max_gleanings", 0) >= 2, "max_gleanings should be at least 2 for dense entity capture"
    
    entity_types = entity_extraction.get("entity_types", [])
    expected_types = {"Person", "Company", "Role", "Technology", "Skill", "Competency", "Project", "Achievement", "Story", "Metric"}
    assert expected_types.issubset(set(entity_types)), f"Missing expected entity types: {expected_types - set(entity_types)}"


def test_extract_graph_prompt_contains_resume_domain_examples():
    """Verify that prompts/extract_graph.txt uses software engineering / resume domain few-shots."""
    prompt_file = ROOT_DIR / "prompts" / "extract_graph.txt"
    assert prompt_file.exists(), f"Missing extract_graph.txt at {prompt_file}"

    content = prompt_file.read_text(encoding="utf-8")
    
    # Must contain placeholder tokens
    assert "{entity_types}" in content
    assert "{tuple_delimiter}" in content
    assert "{record_delimiter}" in content
    assert "{completion_delimiter}" in content
    assert "{input_text}" in content

    # Must contain domain-relevant entities (not just hostage/financial examples)
    domain_terms = ["Technology", "Project", "Metric", "Role", "Kubernetes", "Kafka"]
    content_upper = content.upper()
    assert all(term.upper() in content_upper for term in domain_terms), "extract_graph.txt should feature technical few-shot examples"
