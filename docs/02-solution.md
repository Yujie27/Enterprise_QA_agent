# 02 方案与取舍

## 流程

用户问题 → AgentScope 2.0.11 `Agent` + `ReActConfig` → 模型选择本地工具 → 工具结果作为观察回传 → 模型选择继续检索、读取原文或结束 → 输出带引用答案/追问/无法确认状态。交互模式复用同一个 Agent 实例保存上下文。

## 状态与工具

工具为 `search_docs(query, decision_reason, limit)` 与 `read_doc(doc_id, decision_reason)`。`decision_reason` 是模型在调用时填写的一句公开动作理由。资料包含文档 ID、版本、生效日期、适用范围和条款原文。默认每轮工具调用上限为 4。

Trace v2 保存程序版本和资料哈希，记录原始工具观察、轮次、步骤、工具参数、模型公开理由、后续动作及最终回答。`action_summary_source=program_observed_sequence` 明确表示程序归纳；`reason_source=model_tool_argument` 表示工具参数中的模型原话。程序不推断模型的心理依据。被调用上限拒绝的后续动作标记 `executed=false`。

`data/policies_conflict.json` 为相同范围、相同生效日期、未指定优先级的 30/15 日矛盾条款。`data/policies_single.json` 仅移除其中 D02，保留完全相同的 D01。使用同一问题比较两个资料集，验证模型是否从“引用冲突并请求确认”改为“依据唯一规则回答”。

## 取舍

- 采用单 ReAct Agent。当前场景的主要决策可由一个 Agent 完成，多 Agent 会增加协作和调试成本。
- 选 AgentScope 2.0.11，复用 `Agent`、`ReActConfig`、`FunctionTool` 与 `Toolkit` 的循环及工具调用能力；不改写框架本身。
- 本地 JSON + 轻量词项匹配，避免把 3 小时考核范围扩成完整 RAG 平台；检索结果只是演示用，不能当作生产级召回效果。
- 对“出差/差旅、回来/返程、多久/期限”等少量业务表达做显式归一化，并设置最低词项重合数，减少只因“申请”等常见词造成的误召回。
- `--simulate-failure` 仅作为验收入口，让工具异常作为观察返回模型；Trace 会明确标记故障注入。
- 使用合成数据，避免真实制度和隐私内容。
- Mock 模式用于无密钥时验证流程。评审真实决策效果应运行真实模型并提交运行 Trace。
