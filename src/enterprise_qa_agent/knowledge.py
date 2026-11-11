"""Small local corpus and deterministic retrieval helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "policies.json"

QUERY_ALIASES = {
    "差旅费": "差旅费用",
    "出差": "差旅",
    "回来": "返程",
    "回程": "返程",
    "费用申请": "报销申请",
    "费用报销": "报销",
    "多久": "期限",
}


class KnowledgeBase:
    def __init__(self, path: str | Path = DEFAULT_CORPUS, deduplicate: bool = True, match_threshold: str = "original"):
        if match_threshold not in {"original", "one_overlap"}:
            raise ValueError("Unknown match threshold")
        self.match_threshold = match_threshold
        self.deduplicate = deduplicate
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

    @staticmethod
    def expand_query(query: str) -> str:
        """Append a small, explicit set of business synonyms for lexical retrieval."""
        aliases = [canonical for phrase, canonical in QUERY_ALIASES.items() if phrase in query]
        return " ".join([query, *aliases])

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_terms = self._terms(self.expand_query(query))
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
                minimum_overlap = 1 if len(query_terms) <= 2 else 2
                if self.match_threshold == "one_overlap":
                    minimum_overlap = 1
                if len(overlap) >= minimum_overlap:
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
        if self.deduplicate:
            hits = self._fold_duplicates(hits)
        hits.sort(key=lambda item: (-item[0], item[1]["doc_id"], item[1]["section_id"]))
        return [item[1] for item in hits[: max(1, min(limit, 10))]]

    def _fold_duplicates(self, hits):
        """Fold exact evidence before truncation; never infer authority from votes.

        Equality is deliberately conservative: exact text, scope, version and date.
        A copied_from edge is verified against a unique actual matching original
        section. Invalid edges remain separate, including orphaned copies.
        Representatives are chosen ONLY from candidates passing the existing gate.
        """
        sections = [(doc, sec) for doc in self._docs for sec in doc.get("sections", [])]
        by_key = {(doc["doc_id"], sec["section_id"]): (doc, sec) for doc, sec in sections}

        def signature(doc, sec):
            return (sec["text"], doc.get("scope"), doc.get("version"), doc.get("effective_from"))

        groups = {}
        for score, hit in hits:
            doc, sec = by_key[(hit["doc_id"], hit["section_id"])]
            sig = signature(doc, sec)
            origin = doc.get("copied_from")
            valid_origin = None
            if origin:
                matches = [(d, s) for d, s in sections if d["doc_id"] == origin
                           and not d.get("copied_from") and signature(d, s) == sig]
                if len(matches) == 1:
                    valid_origin = (matches[0][0]["doc_id"], matches[0][1]["section_id"])
            # Unverifiable relationships must not silently collapse into another source.
            group_key = ("invalid_origin", doc["doc_id"], sec["section_id"]) if origin and not valid_origin else ("content", sig)
            groups.setdefault(group_key, []).append((score, hit, doc, sec, valid_origin))
        folded = []
        for group in groups.values():
            origin_keys = {item[4] for item in group if item[4]}
            candidates = [item for item in group if (item[1]["doc_id"], item[1]["section_id"]) in origin_keys]
            representative = sorted(candidates or group, key=lambda item: (-item[0], item[1]["doc_id"], item[1]["section_id"]))[0]
            score, hit, _, _, _ = representative
            hit = dict(hit)
            if len(group) > 1 or any(item[2].get("copied_from") for item in group):
                hit["source_info"] = {
                    "grouping": "exact_content_scope_version_date",
                    "representative_policy": "verified_original_candidate" if candidates else "highest_score_then_id",
                    "sources": [{"doc_id": d["doc_id"], "section_id": s["section_id"],
                                 "declared_copied_from": d.get("copied_from"),
                                 "verified_original": {"doc_id": v[0], "section_id": v[1]} if v else None,
                                 "relationship": "verified_copy" if v else "unverified_copy" if d.get("copied_from") else "content_duplicate_only"}
                                for _, _, d, s, v in group],
                }
            folded.append((score, hit))
        return folded

    def read(self, doc_id: str) -> dict[str, Any] | None:
        for doc in self._docs:
            if doc["doc_id"].lower() == doc_id.lower():
                return doc
        return None
