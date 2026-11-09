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


if __name__ == "__main__":
    unittest.main()
