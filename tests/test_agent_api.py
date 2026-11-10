import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agentscope.agent import Agent

from enterprise_qa_agent.agent import RunRecorder, build_agent
from enterprise_qa_agent.knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


class AgentApiTests(unittest.TestCase):
    def test_installed_agentscope_api_builds_agent_and_local_tools(self):
        recorder = RunRecorder(4)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-only-key",
            "OPENAI_MODEL": "test-only-model",
            "OPENAI_BASE_URL": "",
        }):
            agent = build_agent(KnowledgeBase(ROOT / "data" / "policies.json"), recorder)

        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.react_config.max_iters, 5)
        self.assertEqual(
            {tool.name for group in agent.toolkit.tool_groups for tool in group.tools},
            {"search_docs", "read_doc"},
        )

    def test_trace_records_next_action_and_public_decision_basis(self):
        recorder = RunRecorder(4)
        start = recorder.start_turn("报销期限是多少？")
        recorder.begin_tool("search_docs", {"query": "报销期限", "limit": 5})
        recorder.finish_tool("search_docs", "返回 2 条资料")
        recorder.begin_tool("read_doc", {"doc_id": "D01"})
        recorder.finish_tool("read_doc", "已读取文档原文")
        recorder.finish_turn(start, "请补充费用类型。")

        search_result = recorder.events[2]
        self.assertEqual(search_result["next_action"]["tool"], "read_doc")
        self.assertIn("核对原文", search_result["decision_basis"])

    def test_tool_call_limit_is_enforced_per_turn(self):
        recorder = RunRecorder(1)
        recorder.start_turn("第一轮")
        self.assertTrue(recorder.begin_tool("search_docs", {"query": "报销"}))
        self.assertFalse(recorder.begin_tool("read_doc", {"doc_id": "D01"}))
        self.assertTrue(recorder.limit_reached)

        recorder.start_turn("第二轮")
        self.assertTrue(recorder.begin_tool("search_docs", {"query": "差旅"}))


if __name__ == "__main__":
    unittest.main()
