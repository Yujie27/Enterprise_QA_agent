# 运行记录

真实模型运行产生的 JSON Trace 放在 `runs/`。事件包含轮次、步骤、工具参数、返回摘要、后续动作及可公开的简要决策依据，不记录模型内部思维过程。

| 场景 | 模式/状态 | 记录 |
|---|---|---|
| 离线流程演示 | `scripted_mock` / `mock_completed` | `runs/20261109_154529_428163.json` |
| 正常且范围明确 | `agentscope_react` / `completed` | `runs/20261109_171637_918335.json` |
| 范围不明并追问 | `agentscope_react` / `completed` | `runs/20261110_155542_104377.json` |
| 改写后的相似问题 | `agentscope_react` / `completed` | `runs/20261110_161317_256403.json` |
| 上下文追问（两轮） | `agentscope_react` / `completed` | `runs/20261110_163832_520293.json` |
| 资料不足 | `agentscope_react` / `insufficient_evidence` | `runs/20261110_164243_225746.json` |
| 检索工具失败 | `agentscope_react` / `tool_error` | `runs/20261110_164428_799817.json` |
| 达到调用上限 | `agentscope_react` / `incomplete` | `runs/20261110_164002_988324.json` |

`--mock` 记录只说明本地检索和输出链路可运行，不作为真实 Agent 决策证明。工具失败记录使用显式故障注入参数生成，Trace 中包含 `simulated_failure` 标记。
