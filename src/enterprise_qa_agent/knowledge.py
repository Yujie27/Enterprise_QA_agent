"""Small local corpus and deterministic retrieval helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "policies.json"


class KnowledgeBase:
    def __init__(self, path: str | Path = DEFAULT_CORPUS):
        self.path = Path(path)
        self._docs: list[dict[str, Any]] = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _terms(text: str) -> set[str]:
        terms: set[str] = set()
        for token in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
            if "\u4e00" <= token[0] <= "\u9fff":
                terms.update(token[i : i + 2] for i in range(max(1, len(token) - 1)))
                if len(token) == 1:
                    terms.add(token)
            else:
                terms.add(token)
        return terms

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        hits: list[tuple[float, dict[str, Any]]] = []
        for doc in self._docs:
            for section in doc.get("sections", []):
                searchable = " ".join(
                    [doc.get("title", ""), section.get("text", ""), " ".join(doc.get("tags", []))]
                )
                doc_terms = self._terms(searchable)
                overlap = query_terms & doc_terms
                if overlap:
                    # Simple lexical score for the demo; no embedding claim is made.
                    score = len(overlap) / max(1, len(query_terms))
                    hits.append(
                        (
                            score,
                            {
                                "doc_id": doc["doc_id"],
                                "title": doc["title"],
                                "version": doc["version"],
                                "effective_from": doc["effective_from"],
                                "scope": doc["scope"],
                                "section_id": section["section_id"],
                                "text": section["text"],
                                "score": round(score, 3),
                            },
                        )
                    )
        hits.sort(key=lambda item: (-item[0], item[1]["doc_id"], item[1]["section_id"]))
        return [item[1] for item in hits[: max(1, min(limit, 10))]]

    def read(self, doc_id: str) -> dict[str, Any] | None:
        for doc in self._docs:
            if doc["doc_id"].lower() == doc_id.lower():
                return doc
        return None
