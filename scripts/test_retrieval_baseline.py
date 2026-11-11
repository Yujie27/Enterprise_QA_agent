"""Scoring checks using artificial candidates, never the project retriever."""
import unittest

from retrieval_baseline import aggregate, measure


def annotation(evidence, **updates):
    return dict(necessary_evidence=evidence, copy_to_original={}, context_evidence=[],
                mode="scored", no_answer=False, requires_both_conflict_sides=True,
                requires_cross_document_evidence=False, entry_evidence_any_of=[], **updates)


def hit(doc, section):
    return dict(doc_id=doc, section_id=section)


class ScoringTests(unittest.TestCase):
    def test_same_document_requires_both_sections(self):
        gold = annotation([hit("D01", "S1"), hit("D01", "S2")])
        metric = measure(gold, [hit("D01", "S1")])
        self.assertEqual(metric["recall"], .5)
        self.assertTrue(metric["hit"])
        self.assertFalse(metric["conflict_complete"])

    def test_copies_do_not_inflate_or_replace_primary_original_evidence(self):
        gold = annotation([hit("D01", "S1"), hit("D02", "S1")])
        gold["copy_to_original"] = {"C1/S1": "D02/S1", "C2/S1": "D02/S1"}
        metric = measure(gold, [hit("C1", "S1"), hit("C2", "S1")])
        self.assertEqual(metric["recall"], 0)
        self.assertEqual(metric["canonical_recall"], .5)
        self.assertFalse(metric["canonical_conflict_complete"])

    def test_no_answer_context_is_not_unrelated(self):
        gold = annotation([])
        gold.update(no_answer=True, requires_both_conflict_sides=False,
                    context_evidence=[hit("D01", "S1")])
        metric = measure(gold, [hit("D01", "S1")])
        self.assertIsNone(metric["recall"])
        self.assertEqual(metric["no_answer_unrelated_candidates"], [])
        self.assertTrue(metric["no_answer_any_candidate"])

    def test_exploratory_is_excluded_from_denominators(self):
        gold = annotation([])
        gold.update(mode="exploratory", no_answer=None, requires_both_conflict_sides=False)
        metric = measure(gold, [hit("D01", "S1")])
        group = aggregate([{"metrics": metric, "business_answer_kind": "exploratory"}])
        self.assertEqual(group["positive_n"], 0)
        self.assertEqual(group["strict_pass"], [0, 0])

    def test_crossdoc_entry_is_not_full_coverage(self):
        gold = annotation([hit("D10", "S1"), hit("D11", "S1")])
        gold.update(requires_both_conflict_sides=False, requires_cross_document_evidence=True,
                    entry_evidence_any_of=["D10/S1"])
        metric = measure(gold, [hit("D10", "S1")])
        self.assertTrue(metric["crossdoc_entry_hit"])
        self.assertFalse(metric["crossdoc_all_evidence"])


if __name__ == "__main__":
    unittest.main()
