import json
import pickle
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

def load_chunks() -> list[dict]:
    if not settings.chunks_path.exists():
        return []
    chunks = []
    with settings.chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks

def _load_pickle(path: Path):
    if not path.exists():
        return None
    with path.open("rb") as f:
        return pickle.load(f)

def keyword_score(query: str, text: str) -> float:
    query_terms = [t for t in query.lower().replace("/", " ").replace("_", " ").split() if t]
    if not query_terms:
        return 0.0
    low = text.lower()
    hit = sum(1 for t in query_terms if t in low)
    return hit / max(1, len(query_terms))

def search(query: str, top_k: int = 5, doc_type: str | None = None) -> list[dict]:
    chunks = load_chunks()
    if not chunks:
        return []

    vectorizer = _load_pickle(settings.vectorizer_path)
    matrix = _load_pickle(settings.matrix_path)

    candidate_indices = [
        i for i, c in enumerate(chunks)
        if doc_type is None or c.get("doc_type") == doc_type
    ]
    if not candidate_indices:
        return []

    if vectorizer is not None and matrix is not None:
        q_vec = vectorizer.transform([query])
        sub_matrix = matrix[candidate_indices]
        dense_scores = cosine_similarity(q_vec, sub_matrix).flatten()
    else:
        dense_scores = np.zeros(len(candidate_indices))

    candidates = []
    for local_i, idx in enumerate(candidate_indices):
        c = chunks[idx]
        k_score = keyword_score(query, c["text"])
        d_score = float(dense_scores[local_i])
        score = 0.75 * d_score + 0.25 * k_score
        row = dict(c)
        row["score"] = round(float(score), 6)
        candidates.append(row)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_k]

def ensure_index_ready() -> bool:
    return settings.chunks_path.exists() and settings.vectorizer_path.exists() and settings.matrix_path.exists()
