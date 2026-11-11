import json
import unittest
from pathlib import Path
from enterprise_qa_agent.knowledge import KnowledgeBase

class ThresholdTests(unittest.TestCase):
    def test_matches_all_offline_diagnostic_outputs(self):
        root=Path(__file__).resolve().parents[1]
        file=root/'examples/evaluation/threshold_diagnostic/20261111_v020/results.jsonl'
        for line in file.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            for mode in ['original','one_overlap']:
                expected=[{k:v for k,v in h.items() if k not in {'rank','relevance','supports_requested_answer'}} for h in row['modes'][mode]['candidates']]
                self.assertEqual(KnowledgeBase(root/row['corpus'],match_threshold=mode).search(row['query'],row['k']),expected)

    def test_empty_and_zero_overlap_stay_empty(self):
        for mode in ['original','one_overlap']:
            kb=KnowledgeBase(match_threshold=mode)
            self.assertEqual(kb.search(''),[])
            self.assertEqual(kb.search('zzzzzzqx'),[])
        self.assertEqual(KnowledgeBase().match_threshold,'original')
