import unittest
from pathlib import Path

from enterprise_qa_agent.knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(ROOT / "data" / "policies.json")

    def test_search_returns_ids_and_source_metadata(self):
        results = self.kb.search("研发差旅报销期限")
        self.assertTrue(results)
        self.assertIn("doc_id", results[0])
        self.assertIn("text", results[0])
        self.assertIn("scope", results[0])

    def test_read_returns_original_document(self):
        doc = self.kb.read("D02")
        self.assertIsNotNone(doc)
        self.assertIn("15日内", doc["sections"][0]["text"])

    def test_unknown_document_returns_none(self):
        self.assertIsNone(self.kb.read("D99"))

    def test_rewritten_question_retrieves_research_travel_policy(self):
        results = self.kb.search("研发同事出差回来多久要完成费用申请？")
        self.assertTrue(results)
        self.assertEqual(results[0]["doc_id"], "D02")

    def test_unrelated_application_question_does_not_match_on_one_common_word(self):
        self.assertEqual(self.kb.search("公司育儿补贴如何申请？"), [])

    def test_conflicting_corpus_keeps_both_rules_without_arbitration(self):
        kb = KnowledgeBase(ROOT / "data" / "policies_conflict.json")
        hits = kb.search("普通费用报销期限")
        self.assertEqual({hit["doc_id"] for hit in hits}, {"D01", "D02"})
        self.assertEqual(len({hit["scope"] for hit in hits}), 1)
        self.assertEqual(len({hit["effective_from"] for hit in hits}), 1)
        self.assertIn("30日内", kb.read("D01")["sections"][0]["text"])
        self.assertIn("15日内", kb.read("D02")["sections"][0]["text"])

    def test_single_rule_corpus_removes_only_the_conflicting_document(self):
        single = KnowledgeBase(ROOT / "data" / "policies_single.json")
        conflict = KnowledgeBase(ROOT / "data" / "policies_conflict.json")
        self.assertEqual(single.read("D01"), conflict.read("D01"))
        self.assertIsNone(single.read("D02"))
        self.assertEqual({hit["doc_id"] for hit in single.search("普通费用报销期限")}, {"D01"})


if __name__ == "__main__":
    unittest.main()
