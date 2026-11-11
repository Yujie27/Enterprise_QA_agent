import json
from pathlib import Path
import tempfile
import unittest

from enterprise_qa_agent.knowledge import KnowledgeBase


def document(name, text="报销费用发生后30日内提交。", **fields):
    return dict(doc_id=name, title="报销期限", scope="全体员工", version="1", effective_from="2026-01-01",
                tags=["报销", "期限"], sections=[dict(section_id=name + "-part", text=text)], **fields)


class DedupTests(unittest.TestCase):
    def search(self, docs):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
            return KnowledgeBase(path).search("报销期限", 5)

    def test_non_copy_prefix_and_changed_count_development_variant(self):
        original = document("zeta", "报销费用发生后15日内提交。")
        others = [document(f"archive-{n}", original["sections"][0]["text"], copied_from="zeta") for n in range(17)]
        hits = self.search([*others, original, document("omega")])
        self.assertEqual({h["doc_id"] for h in hits}, {"zeta", "omega"})

    def test_different_numbers_and_units_and_anchors_remain(self):
        texts = ["报销费用发生后30日内提交。", "报销费用发生后15日内提交。", "报销费用发生后15工作日内提交。", "报销费用返程后15日内提交。", "报销费用发生后15自然日内提交。"]
        self.assertEqual(len(self.search([document(str(n), t) for n, t in enumerate(texts)])), 5)

    def test_metadata_differences_remain(self):
        docs = [document(str(n)) for n in range(4)]
        docs[1]["scope"] = "研发"
        docs[2]["version"] = "2"
        docs[3]["effective_from"] = "2026-02-01"
        self.assertEqual(len(self.search(docs)), 4)

    def test_internal_conflict_remains(self):
        doc = document("one")
        doc["sections"].append(dict(section_id="other", text="报销费用发生后15日内提交。"))
        self.assertEqual(len(self.search([doc])), 2)

    def test_invalid_origins_not_merged_or_fabricated(self):
        docs = [document("root"), document("orphan", copied_from="absent"), document("different", "报销费用发生后15日内提交。", copied_from="root")]
        hits = self.search(docs)
        self.assertEqual(len(hits), 3)
        self.assertTrue(all(s["verified_original"] is None for h in hits for s in h.get("source_info", {}).get("sources", [])))

    def test_equal_content_without_relationship_is_not_called_copy(self):
        hits = self.search([document("a"), document("b")])
        self.assertEqual(len(hits), 1)
        self.assertTrue(all(s["relationship"] == "content_duplicate_only" for s in hits[0]["source_info"]["sources"]))
