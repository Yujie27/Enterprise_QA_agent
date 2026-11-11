# 本人运行与复核记录

## 运行信息

- 日期：2026-11-11
- 当前 commit：`038f3f20119c1c4ef062390bf80faaf461ad59b1`（`feat: improve retrieval evidence handling and grounded answers`）。复核时工作区另有未提交的文档与脚本改动，本笔记不对其做结论。
- 本次实际用时：4分钟以内，不包含完整准备与复核时间。
- 亲自执行的命令：三组资料变更对照由本人直接在终端执行，命令只指定输入与配置，不指定工具路径。

```powershell
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/conflict.json --trace-dir examples/runs "报销期限多久？"
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/single.json --trace-dir examples/runs "报销期限多久？"
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/modified.json --trace-dir examples/runs "报销期限多久？"
```

需要说明：Trace 未保存终端命令原文，以上是按 trace 中记录的问题、配置和语料哈希对齐的复现命令，不作为终端历史的逐字还原。预算触顶案例（C11）是复用同一源码候选已保存的 trace，本次没有重跑，也没有改动该文件。复核只读取 trace、语料与源码，没有重新生成任何回答。

## 冲突案例

- 资料文件：[conflict.json](../examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/conflict.json)，sha256 `26d2059e88b8a3b446c6d25ab96df3a0e1d80e0e526e0dc327883c40c4d22bcf`
- Trace 路径：[20261111_134700_661883.json](../examples/runs/20261111_134700_661883.json)
- 模型实际取得的条款：第 1 次 `search_docs` 同时返回 D01-S1“费用报销应在费用发生后30日内提交申请。”与 D02-S1“费用报销应在费用发生后15日内提交申请。”；第 2 次 `read_doc(D01)`、第 3 次 `read_doc(D02)` 返回的全文各自只有一节，文字与检索片段一致。三段返回的 `version` 均为 `2026-01`、`effective_from` 均为 `2026-01-01`、`scope` 均为“未提供”。
- 我的判断及依据：符合预期，回答有据。我先看工具实际返回再判断，依据是两次 `read_doc` 的 `sections[0].text` 与回答引用逐字一致，回答并列 30 日与 15 日、指出同版本同生效日、指出适用范围缺失且无优先或替代说明，没有擅自选定一个期限。虽然资料库里本就存在这两条期限，但判断依据是模型确实取到了它们，而不是我知道语料里有。
- 我发现的问题：trace 中的“下一请求”只是程序观察到的动作序列，"本轮工具调用结束"也不是模型说了“结束”，两者都不构成因果推理证据。回答里“因存在未决冲突而停止回答”属于模型自述，仍需人工对照原文才能确认，程序没有做语义校验。

## 删除冲突方与修改期限的对照

- 三次实际回答：（1）[30 日 / 15 日冲突](../examples/runs/20261111_134700_661883.json)：并列两条原文，说明不能自行选择，请求确认适用制度；（2）[只保留 D01](../examples/runs/20261111_134759_772822.json)：回答费用发生后 30 日内，同时保留适用范围与“自然日还是工作日”的缺口；（3）[同 ID 改为 45 日](../examples/runs/20261111_135104_474854.json)：回答费用发生后 45 日内，并说明只有单一条款。
- 回答是否随资料变化：是。工具路径分别为 3、2、3 次：冲突组 search→read(D01)→read(D02)；单条款组 search→read(D01)；修改组 search→search→read(D01)。
- 引用是否支持回答：支持。三组引用的 D01-S1/D02-S1 均与当次工具返回原文一致；修改组的引用是 45 日，没有沿用旧的 30 日，也没有补造例外条款。
- 我的判断及依据：符合“只改资料、看答案是否跟随”的设计意图。依据是每组回答中的数字能在同一 trace 的 `tool_result.observation` 里找到出处：冲突组来自 D02-S1 的 15 日与 D01-S1 的 30 日，单条款组来自 D01-S1 的 30 日，修改组来自 D01-S1 的 45 日。修改组我还额外核对了第 2 次检索返回的仍是同一个 `D01-S1` 与 45 日原文，因此不存在新旧值混用。三组 `status` 都是 `completed`，这只表示 Agent 正常结束，不是业务正确性的证明；修改组还有一次未增加新证据的补充检索。三条记录不能推出整体准确率，也不能说明过度追查问题已解决。

## 预算触顶案例

- Trace 路径：[20261111_124817_283039.json](../examples/evaluation/dg_targeted/20261111_v020/trials/sessions/C11_r1_dg_targeted/traces/20261111_124817_283039.json)，语料 [complement.json](../examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/complement.json)（sha256 `484efa2062c4e47183b2a02017f819d67b5a91a43c5c78a0d2bed7744ea289b6`），问题“报销期限和需要的材料分别是什么？”，配置 dedup / one_overlap / dg_targeted，预算 4。
- 证据已经充分的步骤：第 1 步。第一次 `search_docs` 已同时返回 D01-S1“费用报销应在费用发生后30日内提交申请。”和 D04-S1“费用报销申请须附合规票据。”，并带 `doc_id`、`section_id`、`version`、`effective_from`、`scope`。我对照语料文件确认：complement.json 只有 D01、D04 两份资料，各只有一节，所以第 1 步返回的就是这两份资料的全文条款，“期限”和“材料”的依据在第 1 步结束时都已到手。
- 后续是否出现无效追查：有。第 2、3 步返回的仍是同一对 `(doc_id, section_id, text)`，只有 `score` 在变（0.333/0.167 → 0.5/0.3 → 0.333/0.333），没有新增必要证据。第 4 步 `read_doc(D01)` 返回的原文仍然只有 D01-S1 一节，没有新条款，边际作用只在于确认 D01 没有其他节。因此 4 次调用里真正必要的是第 1 次。这里要区分“无新增证据”与“无必要”：第 4 步是留痕核对，可以解释为合理但非必要，第 2、3 步属于重复检索。
- 被拒绝的请求：第 5 次，`read_doc(D04)`。记录上，第 4 步的 `next_action` 里该请求 `executed: false`，随后 step 5 的事件类型是 `limit`，`summary` 为“工具调用上限 4 已达到，拒绝继续执行”，events 中没有对应的 `tool_result`，之后直接进入 `assistant_message`。源码核对一致：`RunRecorder.begin_tool` 在 `turn_tool_calls >= max_tool_calls` 时只追加 `limit` 事件并返回 `False`，`search_docs` / `read_doc` 在返回 `False` 时立即返回 `tool_call_limit_reached` 错误，不会进入 `corpus.read`。所以该请求确实被拒绝、没有执行，D04 全文从未被模型读到。
- 我对业务结果和执行状态的判断：业务上“答案有据”，执行上“未完成”，两者都成立且互不抵消。业务依据是两条引用与语料原文逐字一致，回答同时声明 D04 全文未读、材料清单与适用范围无法确认，没有编造票据种类或附件清单。执行依据是 `status` 为 `incomplete`，且回答开头“未完成：达到工具调用上限（4）。”是 `cli.py` 在命中上限时加的程序前缀，不是模型措辞。另外我用资料文件事后确认：即使第 5 次执行，D04 也只有 D04-S1 一节，不会出现新证据；这个结论是我事后核对得到的，不能倒推成模型当时判断“不必读”。

为什么“答案有据”和“执行完成”要分开评价：`status` 是程序对流程的判定，只反映有没有触顶、有没有工具失败，它不含任何语义判断；而“答案有据”要求把回答里的每个数字和引用回查到工具实际返回的原文。两者会朝相反方向出错——本轮是执行未完成但答案有据；反例则是执行 `completed` 但业务不成立，例如 C06 主结论正确却附加了无来源的逾期判断，X04 顺序变体补造了“同层级”。若只看 `status`，会把有据的触顶记录误判成失败，也会把 `completed` 的编造当成通过；若只看答案，又会忽略“本该更早结束却耗尽了预算”这一执行缺陷。

## 我仍不能确认的事项

- 三条 Trace 的生成时间为 13:47:00—13:51:04，该跨度不包含完整准备与复核时间。
- 第 2、3 次重复检索是模型自身冗余，还是结束提示不足导致：trace 只保存公开动作理由，不保存内部推理，无法区分。
- 4 次调用之间是否每次都有一次新的模型决策：同一次模型响应可以批量请求工具，程序摘要只记录观察到的顺序，不能证明相邻动作之间存在模型调用。
- 这条触顶记录能否代表其他模型或其他运行：单次运行，存在随机性；该记录也未计入本轮 19 次新运行的分母。
- 期限与材料的适用边界：两份资料的 `scope` 均为“未提供”，原文也未说明“日”是自然日还是工作日，所以 30 日与“合规票据”对具体部门、费用类型的适用性仍无法确认。
