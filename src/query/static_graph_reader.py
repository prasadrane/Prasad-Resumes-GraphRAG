"""
static_graph_reader.py — Fast static Parquet/JSON reader for pre-indexed GraphRAG artifacts in serverless environments.
Reads graph entities and communities directly from pre-computed output parquet/json files without graphrag CLI subprocess.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"

def read_precomputed_entities() -> List[Dict[str, Any]]:
    """Read pre-computed entities from output graph artifacts if available."""
    entities = []
    # Check for exported JSON graph or parquet outputs
    json_path = OUTPUT_DIR / "graph_entities.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback to reading MASTER_RESUME.txt directly for fast static context
    master_resume = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_resume.exists():
        with open(master_resume, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            return [{"title": "Master Resume Context", "content": "\n".join(lines[:50])}]
            
    return entities

def search_static_graph(query_keywords: List[str]) -> List[str]:
    """Execute fast keyword match over static pre-computed entities in < 1 second."""
    entities = read_precomputed_entities()
    if not entities or not query_keywords:
        return []
        
    matched = []
    lower_kws = [kw.lower() for kw in query_keywords]
    for entity in entities:
        text = str(entity.get("content", "")) + " " + str(entity.get("title", ""))
        if any(kw in text.lower() for kw in lower_kws):
            matched.append(text[:300])
            
    return matched[:10]
