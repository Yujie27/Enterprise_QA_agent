import os
import unittest
from unittest.mock import patch
from enterprise_qa_agent.agent import RunRecorder, build_agent, SYSTEM_PROMPT, DG_TARGETED_PROMPT
from enterprise_qa_agent.knowledge import KnowledgeBase

class DgPromptTests(unittest.TestCase):
    def test_only_prompt_changes_when_strategy_enabled(self):
        captures=[]
        for enabled in [False,True]:
            recorder=RunRecorder(4);recorder.dg_targeted=enabled
            with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'test-only'}), patch('agentscope.agent.Agent') as factory:
                build_agent(KnowledgeBase(match_threshold='one_overlap'),recorder)
                captures.append(factory.call_args.kwargs)
        self.assertEqual(captures[0]['system_prompt'],SYSTEM_PROMPT)
        self.assertEqual(captures[1]['system_prompt'],SYSTEM_PROMPT+DG_TARGETED_PROMPT)
        def tools(c):return {t.name:t.input_schema for g in c['toolkit'].tool_groups for t in g.tools}
        self.assertEqual(tools(captures[0]),tools(captures[1]))
        self.assertEqual(captures[0]['react_config'],captures[1]['react_config'])
        self.assertFalse(RunRecorder(4).dg_targeted)
