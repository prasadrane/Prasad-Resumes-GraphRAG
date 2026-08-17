"""Entity resolution for GraphRAG knowledge graphs.

Merges duplicate entities (e.g. "AWS" / "Amazon Web Services" / "AWS Cloud") using
string similarity + optional embedding-based semantic similarity. Operates on lists
of entity dicts extracted from the GraphRAG output parquet files.

Usage (standalone):
    resolver = EntityResolver()
    resolved_entities, merged = resolver.resolve(entities)

Usage (with parquet post-processing):
    See scripts/postprocess_graph.py for the full CLI pipeline.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

logger = logging.getLogger(__name__)

# Types that should trigger semantic (embedding) comparison when available.
_SEMANTIC_TYPES: frozenset[str] = frozenset({"Technology", "Skill", "Competency"})


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class ResolutionPair:
    """Records one merge decision."""
    canonical: str          # preferred / surviving name
    merged_into: str        # discarded / merged variant
    string_score: float     # SequenceMatcher ratio
    semantic_score: float | None  # None if not applicable or unavailable
    type_: str              # entity type of the pair


# ── Union-Find helper ────────────────────────────────────────────────────────

class _UnionFind:
    """Minimal union-find for grouping indices."""

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1
        return True


# ── EntityResolver ────────────────────────────────────────────────────────────

class EntityResolver:
    """Detect and resolve duplicate entities in a GraphRAG entity set.

    Parameters
    ----------
    string_threshold : float
        Minimum SequenceMatcher ratio (0..1) to consider two names similar.
    semantic_threshold : float
        Extra boost required for SEMANTIC types when embeddings are available.
        Combined score is an AND gate: both thresholds must be exceeded independently.
    embed_fn : callable(str, str) -> list[float] | None, optional
        A function ``(text, model_name)`` that returns a normalized embedding
        vector (list[float]) or ``None`` when unavailable. If omitted, only
        string similarity is used.
    """

    def __init__(
        self,
        string_threshold: float = 0.85,
        semantic_threshold: float = 0.80,
        embed_fn: Any = None,
    ) -> None:
        self.string_threshold = string_threshold
        self.semantic_threshold = semantic_threshold
        self._embed_fn = embed_fn
        self._canonical_map: dict[str, str] = {}      # merged_name → canonical_name
        self._pairs: list[ResolutionPair] = []         # audit trail

    # ── Public API ─────────────────────────────────────────────────────────

    def resolve(
        self,
        entities: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[ResolutionPair]]:
        """Resolve duplicate entities in-place and return cleaned set.

        Parameters
        ----------
        entities : list[dict]
            Each dict must contain at least ``"name"`` and ``"type"`` keys
            (as produced by the GraphRAG ``create_final_entities`` parquet).

        Returns
        -------
        (resolved_entities, pairs)
            ``resolved_entities`` — deduplicated list with updated names/types.
            ``pairs`` — audit log of every merge performed.
        """
        self._canonical_map.clear()
        self._pairs.clear()
        self._entities = entities  # needed by _cluster_type

        if not entities:
            return [], []

        # Bucket by type — only merge within same type.
        buckets: dict[str, list[int]] = {}  # type → list of indices
        for i, ent in enumerate(entities):
            t = ent.get("type", "Unknown")
            buckets.setdefault(t, []).append(i)

        # Cluster within each bucket using union-find.
        clusters: dict[int, list[int]] = {}  # lead_entity_index → [member_indices]
        for type_, indices in buckets.items():
            type_clusters = self._cluster_type(indices, type_)
            clusters.update(type_clusters)

        # Build resolved entity dicts from clusters.
        resolved: list[dict[str, Any]] = []
        for canonical_idx, member_indices in clusters.items():
            first = entities[member_indices[0]]
            other_names = [entities[j]["name"] for j in member_indices[1:]]
            # Start with canonical row and absorb attributes from all others.
            merged_attrs: dict[str, Any] = dict(first)
            merged_attrs["_merged_from"] = other_names
            for j in member_indices[1:]:
                m = entities[j]
                for k, v in m.items():
                    if k == "name":
                        continue
                    existing = merged_attrs.get(k)
                    if not existing and isinstance(v, str) and v:
                        merged_attrs[k] = v
                    elif isinstance(existing, str) and isinstance(v, str) and len(v) > len(existing):
                        merged_attrs[k] = v
            resolved.append(merged_attrs)

        return resolved, self._pairs

    def update_relationships(
        self,
        relationships: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
        """Relabel relationships to use canonical entity names after resolution.

        Parameters
        ----------
        relationships : list[dict]
            Each dict must contain ``"source"`` and ``"target"`` keys
            (as produced by ``create_final_relationships`` parquet).

        Returns
        -------
        (updated, relabeled)
            ``relabeled`` records each change as ``(before, after, other_side)``.
        """
        if not self._canonical_map:
            return relationships, []

        updated: list[dict[str, Any]] = []
        relabeled: list[tuple[str, str, str]] = []

        for rel in relationships:
            src = rel.get("source", "")
            tgt = rel.get("target", "")
            new_src = self._canonical_map.get(src, src)
            new_tgt = self._canonical_map.get(tgt, tgt)
            if new_src != src:
                relabeled.append((src, new_src, tgt))
            if new_tgt != tgt:
                relabeled.append((new_src, src, tgt))  # source unchanged; record target change
            rel_copy = dict(rel)
            rel_copy["source"] = new_src
            rel_copy["target"] = new_tgt
            updated.append(rel_copy)

        return updated, relabeled

    # ── Internal helpers ───────────────────────────────────────────────────

    def _cluster_type(
        self,
        indices: list[int],
        type_: str,
    ) -> dict[str, list[int]]:
        """Cluster entity indices of a single type into (lead_index → [member_indices]).

        Uses union-find with pairwise similarity comparison. The canonical name for
        each cluster is the name of the lead (first-found) entity.
        """
        n = len(indices)
        if n <= 1:
            if n == 1:
                idx = indices[0]
                name = self._entities[idx]["name"]
                self._canonical_map[name] = name  # identity mapping (present but no merge)
            return {indices[0]: indices} if n == 1 else {}

        uf = _UnionFind(n)
        candidate_pairs = self._generate_candidate_pairs(indices)

        for i, j in candidate_pairs:
            si, sj = indices[i], indices[j]
            ni = self._entities[si]["name"]
            nj = self._entities[sj]["name"]

            # Skip already-merged variants (pointing elsewhere).
            canon_i = self._canonical_map.get(ni, ni)
            canon_j = self._canonical_map.get(nj, nj)
            if canon_i != ni or canon_j != nj:
                continue

            ss = self._string_similarity(ni, nj)
            if type_ in _SEMANTIC_TYPES and self._embed_fn:
                sem = self._semantic_similarity(ni, nj)
                passes = ss >= self.string_threshold and sem >= self.semantic_threshold
            else:
                passes = ss >= self.string_threshold
            if passes:
                uf.union(i, j)

        # Group by representative.
        groups: dict[int, list[int]] = {}
        for i in range(n):
            root = uf.find(i)
            groups.setdefault(root, []).append(indices[i])

        # Record merges and build cluster map keyed by leading entity index.
        clusters: dict[int, list[int]] = {}
        for rep, members in groups.items():
            lead_idx = members[0]
            lead_name = self._entities[lead_idx]["name"]
            canonical_name = self._canonical_map.get(lead_name, lead_name)

            for midx in members[1:]:
                mname = self._entities[midx]["name"]

                # Skip if already mapped to a different canonical name from a previous run.
                if mname in self._canonical_map and self._canonical_map[mname] != canonical_name:
                    continue

                # Register merge: merged entity → canonical.
                self._canonical_map[mname] = canonical_name

                ss = self._string_similarity(mname, canonical_name)
                # Only use embeddings for semantic entity types (Technology/Skill/Competency)
                if self._embed_fn and type_ in _SEMANTIC_TYPES:
                    sem = self._semantic_similarity(mname, canonical_name)
                else:
                    sem = None
                self._pairs.append(ResolutionPair(
                    canonical=canonical_name,
                    merged_into=mname,
                    string_score=ss,
                    semantic_score=sem,
                    type_=type_,
                ))

            clusters[lead_idx] = members

        return clusters

    def _generate_candidate_pairs(self, indices: list[int]) -> set[tuple[int, int]]:
        """Generate candidate index pairs using inverted n-gram index and prefix blocking.
        
        For small sets (<= 30 items), returns all pairs. For larger sets, returns only
        pairs sharing character trigrams, tokens, or common prefixes/lengths, reducing
        comparisons from O(N^2) to O(N log N).
        """
        n = len(indices)
        if n <= 30:
            return {(i, j) for i in range(n) for j in range(i + 1, n)}

        candidate_pairs: set[tuple[int, int]] = set()
        trigram_index: dict[str, list[int]] = {}
        token_index: dict[str, list[int]] = {}
        short_names: list[int] = []

        for i, idx in enumerate(indices):
            name = self._entities[idx]["name"]
            norm = re.sub(r"[^\w\s]", "", name.lower()).strip()
            tokens = [t for t in norm.split() if t]
            
            if len(norm) <= 4:
                short_names.append(i)
            else:
                for k in range(len(norm) - 2):
                    tri = norm[k : k + 3]
                    trigram_index.setdefault(tri, []).append(i)

            for token in tokens:
                if len(token) >= 2:
                    token_index.setdefault(token, []).append(i)

        for tri_members in trigram_index.values():
            if len(tri_members) > 1 and len(tri_members) < 200:
                for a_pos in range(len(tri_members)):
                    for b_pos in range(a_pos + 1, len(tri_members)):
                        candidate_pairs.add((min(tri_members[a_pos], tri_members[b_pos]),
                                             max(tri_members[a_pos], tri_members[b_pos])))

        for tok_members in token_index.values():
            if len(tok_members) > 1 and len(tok_members) < 200:
                for a_pos in range(len(tok_members)):
                    for b_pos in range(a_pos + 1, len(tok_members)):
                        candidate_pairs.add((min(tok_members[a_pos], tok_members[b_pos]),
                                             max(tok_members[a_pos], tok_members[b_pos])))

        for a_pos in range(len(short_names)):
            for b_pos in range(a_pos + 1, len(short_names)):
                candidate_pairs.add((min(short_names[a_pos], short_names[b_pos]),
                                     max(short_names[a_pos], short_names[b_pos])))

        return candidate_pairs

    @staticmethod
    def _string_similarity(a: str, b: str) -> float:
        """Return SequenceMatcher ratio between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _semantic_similarity(self, a: str, b: str) -> float:
        """Compute cosine similarity between two text embeddings.

        Falls back to 0.0 when embedding service is unavailable.
        """
        try:
            ea = self._embed_fn(a, "sentence-transformers/all-MiniLM-L6-v2")
            eb = self._embed_fn(b, "sentence-transformers/all-MiniLM-L6-v2")
            if ea is None or eb is None:
                return 0.0
            return float(self._cosine(ea, eb))
        except Exception:
            logger.debug("Embedding lookup failed for %r vs %r", a, b)
            return 0.0

    def _combined_similarity(self, a: str, b: str, type_: str) -> float:
        """Composite score: AND-gate for semantic types, pure string otherwise."""
        ss = self._string_similarity(a, b)

        if type_ in _SEMANTIC_TYPES and self._embed_fn:
            sem = self._semantic_similarity(a, b)
            # AND gate: requires BOTH string AND semantic thresholds to pass
            if ss < self.string_threshold or sem < self.semantic_threshold:
                return 0.0  # either gate failed
            return min(ss, sem)  # both passed; conservative combined score
        return ss

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


# ── Optional pre-configured factory ──────────────────────────────────────────

def create_entity_resolver_with_embeddings(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    string_threshold: float = 0.85,
    semantic_threshold: float = 0.80,
) -> EntityResolver:
    """Create an EntityResolver loaded with sentence-transformers embeddings.

    Returns a resolver where TECHNOLOGY/Skill/Competency types get a semantic
    boost in addition to string similarity. Falls back gracefully if
    ``sentence_transformers`` is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found,unused-ignore]
        cache_dir = None
        try:
            import os
            cache_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME", None)
        except Exception:
            pass
        encoder = SentenceTransformer(model_name, cache_folder=cache_dir)

        def embed_fn(text: str, _model: str) -> list[float] | None:
            vec = encoder.encode(text, normalize_embeddings=True, show_progress_bar=False)
            return vec.tolist()

        return EntityResolver(
            string_threshold=string_threshold,
            semantic_threshold=semantic_threshold,
            embed_fn=embed_fn,
        )
    except ImportError:
        logger.info("sentence_transformers not installed — returning string-only resolver")
        return EntityResolver(
            string_threshold=string_threshold,
            semantic_threshold=semantic_threshold,
        )
