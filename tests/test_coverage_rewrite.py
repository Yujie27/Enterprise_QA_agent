import unittest
import importlib.util
from pathlib import Path
from enterprise_qa_agent.agent import RunRecorder
from enterprise_qa_agent.knowledge import KnowledgeBase


class CoverageTests(unittest.TestCase):
    def test_enabled_tools_count_real_searches_and_reject_fifth(self):
        import json
        import os
        from unittest.mock import patch
        from enterprise_qa_agent.agent import build_agent
        root = Path(__file__).resolve().parents[1]
        kb = KnowledgeBase(root / "data/policies.json", deduplicate=False)
        r = RunRecorder(4)
        r.demand_rewrite = True
        r.start_turn("期限与材料")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "OPENAI_MODEL": "test-only"}):
            agent = build_agent(kb, r)
        tool = next(t for g in agent.toolkit.tool_groups for t in g.tools if t.name == "search_docs")
        self.assertIn("coverage", tool.input_schema["properties"])
        with patch.object(kb, "search", wraps=kb.search) as search:
            for n in range(4):
                payload = json.loads(tool._func("报销期限", "定位缺失依据", coverage={"missing": ["期限"]}).content[0].text)
                self.assertEqual(payload["retrieval_statistics"]["underlying_queries_this_call"], 1)
            denied = json.loads(tool._func("材料", "定位缺失依据").content[0].text)
            self.assertEqual(search.call_count, 4)
            self.assertEqual(denied["error"], "tool_call_limit_reached")
        self.assertEqual(r.tool_calls, 4)
        self.assertEqual(sum(e["type"] == "coverage_report" for e in r.events), 4)

    def test_disabled_agent_keeps_sealed_prompt_and_tool_schemas(self):
        import os
        from unittest.mock import patch
        from enterprise_qa_agent.agent import build_agent, SYSTEM_PROMPT
        root = Path(__file__).resolve().parents[1]
        file = root / "examples/evaluation/demand_rewrite/20261110_v020/sealed_a_dedup/src/enterprise_qa_agent/agent.py"
        spec = importlib.util.spec_from_file_location("enterprise_qa_agent._sealed_agent", file)
        sealed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sealed)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "OPENAI_MODEL": "test-only"}):
            current = build_agent(KnowledgeBase(), RunRecorder(4))
            old = sealed.build_agent(KnowledgeBase(), sealed.RunRecorder(4))
        self.assertEqual(SYSTEM_PROMPT, sealed.SYSTEM_PROMPT)
        def schemas(agent):
            return {t.name: (t.description, t.input_schema) for g in agent.toolkit.tool_groups for t in g.tools}
        self.assertEqual(schemas(current), schemas(old))

    def test_statistics_separate_novelty_from_semantic_coverage(self):
        r = RunRecorder(4)
        r.start_turn("期限和材料")
        hit = dict(doc_id="d", section_id="s", text="原文")
        self.assertEqual(r.retrieval_statistics([hit], "a")["new_evidence_count"], 1)
        stats = r.retrieval_statistics([hit], "b")
        self.assertEqual(stats["new_evidence_count"], 0)
        self.assertFalse(stats["exact_query_repeated"])
        self.assertTrue(r.retrieval_statistics([hit], "b")["exact_query_repeated"])
        r.start_turn("下一轮")
        self.assertEqual(r.retrieval_statistics([hit], "b")["new_evidence_count"], 1)

    def test_model_coverage_is_not_program_verified_truth(self):
        r = RunRecorder(4)
        r.demand_rewrite = True
        r.coverage_note({"needs": ["条件", "流程"], "covered": [], "missing": ["流程"]})
        self.assertEqual(r.events[0]["source"], "model_tool_argument")
        self.assertFalse(r.events[0]["validated_semantically"])

    def test_original_mode_matches_all_frozen_raw_results(self):
        import json
        root = Path(__file__).resolve().parents[1]
        file = root / "examples/evaluation/retrieval_baseline/20261110_raw_query_v020/results.jsonl"
        for line in file.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            expected = [{k: v for k, v in h.items() if k not in {"rank", "corpus_metadata"}} for h in r["candidates"]]
            self.assertEqual(KnowledgeBase(root / r["corpus"], deduplicate=False).search(r["query"], r["k"]), expected)

    def test_dedup_mode_matches_sealed_implementation(self):
        root = Path(__file__).resolve().parents[1]
        file = root / "examples/evaluation/demand_rewrite/20261110_v020/sealed_a_dedup/src/enterprise_qa_agent/knowledge.py"
        spec = importlib.util.spec_from_file_location("sealed_knowledge", file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        corpus = root / "examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/majority.json"
        self.assertEqual(KnowledgeBase(corpus).search("报销期限", 5), mod.KnowledgeBase(corpus).search("报销期限", 5))
