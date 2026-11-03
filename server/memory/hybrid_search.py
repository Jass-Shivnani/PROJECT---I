"""
Dione AI — Hybrid Memory Search with Temporal Decay & MMR (Maximal Marginal Relevance)
Adapted from OpenClaw's memory retrieval and context ranking architecture.
Combines semantic similarity, exponential temporal decay, and diversity reranking.
"""

import math
import time
from typing import List, Dict, Any, Optional
import numpy as np
from loguru import logger


def calculate_temporal_decay(age_in_days: float, half_life_days: float = 30.0, is_evergreen: bool = False) -> float:
    """
    OpenClaw exponential temporal decay:
    multiplier = exp(-lambda * age_in_days), where lambda = ln(2) / half_life_days.
    Evergreen memories (user profile, name, persistent preferences) never decay (multiplier = 1.0).
    """
    if is_evergreen or half_life_days <= 0:
        return 1.0
    decay_lambda = math.log(2) / half_life_days
    clamped_age = max(0.0, age_in_days)
    return math.exp(-decay_lambda * clamped_age)


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors."""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


def maximal_marginal_relevance(
    query_embedding: np.ndarray,
    candidate_embeddings: List[np.ndarray],
    candidate_items: List[Dict[str, Any]],
    top_k: int = 5,
    lambda_param: float = 0.65,
    half_life_days: float = 30.0
) -> List[Dict[str, Any]]:
    """
    OpenClaw MMR Re-ranking with Temporal Decay:
    Balances query relevance against redundancy with already selected items.
    score = lambda * (sim(q, doc) * decay) - (1 - lambda) * max(sim(doc, selected))
    """
    if not candidate_items or top_k <= 0:
        return []

    now_ts = time.time()
    n = len(candidate_items)
    selected_indices: List[int] = []
    unselected_indices = list(range(n))

    # Pre-calculate base query similarities and temporal decay
    query_sims = []
    for i, emb in enumerate(candidate_embeddings):
        sim = cosine_similarity(query_embedding, emb)
        created_at = candidate_items[i].get("timestamp_ts", now_ts)
        is_evergreen = candidate_items[i].get("is_evergreen", False)
        age_days = (now_ts - created_at) / (24 * 3600)
        decay = calculate_temporal_decay(age_days, half_life_days=half_life_days, is_evergreen=is_evergreen)
        query_sims.append(sim * decay)

    while len(selected_indices) < min(top_k, n) and unselected_indices:
        best_score = -float("inf")
        best_idx = -1

        for idx in unselected_indices:
            relevance = query_sims[idx]

            # Redundancy penalty: max similarity to any already-selected item
            if selected_indices:
                max_redundancy = max(
                    cosine_similarity(candidate_embeddings[idx], candidate_embeddings[sel])
                    for sel in selected_indices
                )
            else:
                max_redundancy = 0.0

            # MMR formula
            mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx != -1:
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)
        else:
            break

    return [candidate_items[i] for i in selected_indices]
