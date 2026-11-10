# 运行记录

真实模型运行产生的 JSON Trace 放在 `runs/`。v0.2.0 / Trace v2 记录工具观察和模型填写的 `public_decision_reason`（`reason_source=model_tool_argument`）。程序按执行顺序归纳的摘要另标为 `action_summary_source=program_observed_sequence`。不记录模型内部思维过程。

历史记录中的 `decision_basis` 为程序生成的固定描述，不能视为模型原话或独立的决策依据；历史记录不修改。它们仍保存了实际工具调用与答案。

| 场景 | 模式/状态 | 记录 |
|---|---|---|
| 离线流程演示 | `scripted_mock` / `mock_completed` | `runs/20261109_154529_428163.json` |
| 正常且范围明确 | `agentscope_react` / `completed` | `runs/20261109_171637_918335.json` |
| 范围不明并追问（不等于同范围冲突） | `agentscope_react` / `completed` | `runs/20261110_155542_104377.json` |
| 改写后的相似问题 | `agentscope_react` / `completed` | `runs/20261110_161317_256403.json` |
| 上下文追问（两轮） | `agentscope_react` / `completed` | `runs/20261110_163832_520293.json` |
| 资料不足 | `agentscope_react` / `insufficient_evidence` | `runs/20261110_164243_225746.json` |
| 检索工具失败 | `agentscope_react` / `tool_error` | `runs/20261110_164428_799817.json` |
| 达到调用上限 | `agentscope_react` / `incomplete` | `runs/20261110_164002_988324.json` |
| 同范围真实冲突（v0.2.0） | `agentscope_react` / `completed`，引用两条规则并请求确认 | `runs/20261110_175458_096243.json` |
| 移除冲突后的同题对照（v0.2.0） | `agentscope_react` / `completed`，根据 D01 回答 30 日 | `runs/20261110_175227_893715.json` |

上述两个 v0.2.0 对照使用相同问题，资料分别为 `data/policies_conflict.json` 与 `data/policies_single.json`，Trace 中的哈希对应当前资料。单规则记录实际执行了三次检索，没有调用 `read_doc`；引用来自工具返回的原文片段，不能将回答中的“核对原文”表述为已读取全文。

保留的调试历史：`runs/20261110_174032_853724.json` 为早期含“合成冲突资料”标题标签的冲突记录；`runs/20261110_174150_441832.json` 为相应单规则对照，反复检索触顶返回 `incomplete`。这两条对应修改前的资料标题及提示词，不计入最终对照通过证据。

`completed` 表示 Agent 正常结束本轮；冲突记录的业务结论仍为“无法确定，需确认制度”，不是已解决冲突。

`--mock` 记录只说明本地检索和输出链路可运行，不作为真实 Agent 决策证明。工具失败记录使用显式故障注入参数生成，Trace 中包含 `simulated_failure` 标记。
