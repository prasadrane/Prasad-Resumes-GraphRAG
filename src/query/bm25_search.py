"""
bm25_search.py — Pure-Python BM25 Okapi sparse search & Reciprocal Rank Fusion (RRF).

Provides fast, in-memory keyword search and rank fusion to complement dense vector search
across GraphRAG text units, entities, and community summaries.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import pandas as pd


def tokenize_code_and_text(text: str) -> List[str]:
    """Tokenize technical and natural language text, preserving acronyms, code symbols, and numbers."""
    if not text:
        return []
    
    # Normalize common tech symbols
    cleaned = text.lower()
    cleaned = cleaned.replace("c#", "csharp")
    cleaned = cleaned.replace("c++", "cpp")
    cleaned = cleaned.replace(".net", "dotnet")
    
    # Extract alphanumeric words, plus preserved symbols (hyphens, dots in numbers/versions)
    tokens = re.findall(r"[a-z0-9]+(?:[\.\-_%][a-z0-9]+)*|[a-z0-9]+", cleaned)
    
    # Also add standard unigrams for composite tokens
    expanded: List[str] = []
    for tok in tokens:
        expanded.append(tok)
        if tok == "csharp":
            expanded.append("c#")
        elif tok == "dotnet":
            expanded.append(".net")
    return expanded


class BM25Index:
    """In-memory BM25 Okapi index for text retrieval."""

    def __init__(
        self,
        corpus: Sequence[str],
        doc_ids: Optional[Sequence[Any]] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_ids = list(doc_ids) if doc_ids is not None else list(range(self.corpus_size))
        
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.doc_freqs: Dict[str, int] = Counter()
        self.term_freqs: List[Dict[str, int]] = []

        total_length = 0
        for doc in corpus:
            tokens = tokenize_code_and_text(str(doc))
            self.doc_tokens.append(tokens)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len
            
            tf = Counter(tokens)
            self.term_freqs.append(tf)
            for term in tf.keys():
                self.doc_freqs[term] += 1

        self.avg_doc_len = (total_length / self.corpus_size) if self.corpus_size > 0 else 0.0

        # Precompute IDF for all terms in corpus
        self.idf: Dict[str, float] = {}
        for term, freq in self.doc_freqs.items():
            # BM25 standard IDF with smoothing
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        text_col: str = "text",
        id_col: Optional[str] = "id",
        k1: float = 1.5,
        b: float = 0.75,
    ) -> "BM25Index":
        if df.empty or text_col not in df.columns:
            return cls([], [], k1=k1, b=b)
        texts = df[text_col].fillna("").astype(str).tolist()
        ids = df[id_col].tolist() if id_col and id_col in df.columns else list(range(len(texts)))
        index = cls(texts, doc_ids=ids, k1=k1, b=b)
        index._source_df = df
        return index

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Score all documents against query terms and return top_k (doc_index, score) pairs."""
        if self.corpus_size == 0 or not query.strip():
            return []

        query_tokens = tokenize_code_and_text(query)
        scores: List[float] = [0.0] * self.corpus_size

        for term in query_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            
            for doc_idx in range(self.corpus_size):
                tf = self.term_freqs[doc_idx].get(term, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[doc_idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0))
                numer = tf * (self.k1 + 1.0)
                scores[doc_idx] += term_idf * (numer / denom)

        ranked = [(idx, score) for idx, score in enumerate(scores) if score > 0.0]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def search_df(self, query: str, top_k: int = 10) -> pd.DataFrame:
        """Search and return the matching subset of the original DataFrame."""
        if not hasattr(self, "_source_df") or self._source_df.empty:
            return pd.DataFrame()

        results = self.search(query, top_k=top_k)
        if not results:
            return pd.DataFrame(columns=self._source_df.columns)

        indices = [idx for idx, _ in results]
        scores = [score for _, score in results]
        
        matched_df = self._source_df.iloc[indices].copy()
        matched_df["_bm25_score"] = scores
        return matched_df


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Any]],
    k: int = 60,
    weights: Optional[Sequence[float]] = None,
) -> List[Tuple[Any, float]]:
    """Fuse multiple ranked lists into a single ranked list using Reciprocal Rank Fusion (RRF).
    
    Formula: RRF_score(d) = sum_{r in rankings} (weight_r / (k + rank_r(d)))
    """
    if not rankings:
        return []

    if weights is None:
        weights = [1.0] * len(rankings)

    scores: Dict[Any, float] = {}

    for ranking, weight in zip(rankings, weights):
        for rank, item in enumerate(ranking, start=1):
            if item is None:
                continue
            # Some items might be dict or unhashable if not normalized; assume item is hashable ID
            item_key = item
            if isinstance(item, dict) and "id" in item:
                item_key = item["id"]
            
            current_score = scores.get(item_key, 0.0)
            scores[item_key] = current_score + (weight / (k + rank))

    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results
