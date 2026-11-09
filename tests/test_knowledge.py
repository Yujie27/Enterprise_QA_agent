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


if __name__ == "__main__":
    unittest.main()
