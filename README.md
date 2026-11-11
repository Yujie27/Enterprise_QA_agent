# 企业制度问答 Agent（v0.2.0）

## 最终候选评审入口（2026-11-11）

当前候选验收有保留：[验收报告](examples/evaluation/final_acceptance/20261111_v020/summary.md)、[逐条Trace索引](examples/acceptance/README.md)、[候选源码与依赖封存](examples/evaluation/final_acceptance/20261111_v020/candidate/identity.json)。18次原生真实运行17次严格业务通过；另1次受控返回顺序变体存在附加“同层级”断言。不能写成全部无缺陷达标或泛化准确率。

**业务默认没有切换**：dedup开启、original门槛、DG提示策略关闭、demand-rewrite关闭。**本次提交演示候选**显式启用dedup＋one_overlap＋dg-targeted，保持demand-rewrite关闭，每轮4次工具。

```powershell
uv sync --locked
# 首次配置本地.env后，直接演示真实候选；不需要切换源码
uv run --locked python scripts/submission_demo.py normal
uv run --locked python scripts/submission_demo.py conflict
uv run --locked python scripts/submission_demo.py single
uv run --locked python scripts/submission_demo.py replace45
uv run --locked python scripts/submission_demo.py outside
uv run --locked python scripts/submission_demo.py multi
uv run --locked python scripts/submission_demo.py search-failure
uv run --locked python scripts/submission_demo.py read-failure
# 原CLI也可以显式选择候选（默认资料含部门差异）
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted "研发部门差旅报销期限？"
```

演示入口仅选择固定合成输入和候选开关，真实模型自主决定工具路径，不预设答案。模型使用本地`.env`，本批为`deepseek-flash`、OpenAI兼容端点`https://api.deepseek.com/v1`、非流式、`parallel_tool_calls=False`；temperature/top_p/seed未显式设置。不可将密钥写进命令、文档或pyproject.toml。模型可能产生与已存记录不同的结果。

AgentScope 2.0.11负责模型与工具schema接入、ReAct循环、会话消息和权限；本项目负责检索、来源折叠、门槛实验、工具预算和Trace。Mock仅是预设流程检查，不证明模型动态决策。当前没有程序语义/引用断言保证。

已知限制：按需改写尚未证明稳定收益；D/G仅为提示策略；主动关联冲突来源补查尚未实现；简单问题仍可能追查触顶。C06额外逾期判断和顺序变体的“同层级”断言原样保留，未在验收中修复。26项自动测试通过；代码、评测和本轮文档均由AI辅助，候选人亲自完成范围与实际投入用时待本人核实补充。

以下为原有环境说明及历史演示入口；当前候选以本节显式配置为准，实验历史见`examples/evaluation/`，不与提交演示混称。


单 Agent + 本地制度检索工具的 CLI 示例。真实模式使用 AgentScope 2.0.11 的 `Agent` + `ReActConfig`，由模型选择 `search_docs` / `read_doc` 工具；离线模式仅用于检查检索与输出流程，不代表模型决策效果。

## 环境与运行

### 2026-11-11 本人执行的三组资料变更实验

本人亲自执行三组资料变更实验并提供实际输出：[30/15日冲突](examples/runs/20261111_134700_661883.json)、[只留30日](examples/runs/20261111_134759_772822.json)、[改为45日](examples/runs/20261111_135104_474854.json)。实际工具次数分别为3、2、3；第三组有一次未增加新证据的补充检索。[评估记录](docs/03-evaluation.md#2026-11-11-本人执行的三组资料变更对照)由AI据Trace整理，个人审阅结论见[本人运行与复核记录](docs/06-personal-review.md)。

以下完整复现命令与本次Trace的问题、配置及资料哈希一致。Trace未保存终端命令原文，不将这些命令称为终端历史的逐字还原；资料已经存在，无需再次修改资料或重新生成已保存输出。

```powershell
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/conflict.json --trace-dir examples/runs "报销期限多久？"
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/single.json --trace-dir examples/runs "报销期限多久？"
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted --corpus examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design/corpora/modified.json --trace-dir examples/runs "报销期限多久？"
```

这三组使用实验配置：去重开启、one_overlap门槛、DG策略开启，**不启用`--demand-rewrite`**，每轮预算4。程序默认仍为去重开启、original门槛、DG策略关闭、按需改写关闭。三组记录不代表整体准确率100%，也不说明所有结束问题已解决。

要求 Python 3.11+。

```powershell
cd Enterprise_QA_agent
uv sync --locked
Copy-Item .env.example .env
```

编辑 `.env`，填写模型 API 配置后运行真实 Agent：

```powershell
uv run enterprise-qa "报销期限是几天？"
```

多轮上下文追问：

```powershell
uv run enterprise-qa --interactive
```

也可用固定后续消息复现多轮验收：

```powershell
uv run enterprise-qa --interactive "报销期限是多少？" --follow-up "我是研发部门，差旅报销。"
```

工具失败验收入口（只用于测试）：

```powershell
uv run enterprise-qa --simulate-failure search_docs "报销期限是多少？"
```

相同适用范围下的真实冲突与资料替换对照（保持问题不变）：

```powershell
uv run --locked enterprise-qa --corpus data/policies_conflict.json "全体员工普通费用报销期限是多久？"
uv run --locked enterprise-qa --corpus data/policies_single.json "全体员工普通费用报销期限是多久？"
```

冲突资料中 D01 为 30 日、D02 为 15 日，两者范围和生效日期相同且没有优先级。预期列出双方原文并请求确认适用制度；移除 D02 后，预期根据 D01 回答 30 日。资料位于独立文件，默认知识库仍用于部门范围追问。

`.env` 使用 OpenAI 兼容接口参数。支持兼容 OpenAI API 的服务；API 必须支持 tool/function calling。

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=your_tool_calling_model
# 可选：兼容 OpenAI 的自定义接口地址
OPENAI_BASE_URL=
```

没有可用模型时可运行离线流程：

```powershell
uv run enterprise-qa --mock "报销期限是几天？"
```

Mock 是预设的流程演示，只验证工具和数据链路，不证明真实模型会作出相同决策。每次运行会在 `examples/runs/` 写入 JSON Trace。

v0.2.0 Trace 包含程序版本、资料文件名及 SHA-256。`action_summary` 是程序按实际调用顺序归纳的动作摘要；`public_decision_reason` 是模型在工具参数中填写的一句公开理由，来源标为 `model_tool_argument`，最终回答也会说明为何结束。两者均不记录内部思维过程。早期 Trace 的 `decision_basis` 是程序生成的历史字段，不能作为模型理由的证据。

## 评审入口

- 用户与成功标准：[`docs/01-requirements.md`](docs/01-requirements.md)
- 方案与流程：[`docs/02-solution.md`](docs/02-solution.md)
- 测试与限制：[`docs/03-evaluation.md`](docs/03-evaluation.md)
- AI 使用记录：[`docs/04-ai-usage.md`](docs/04-ai-usage.md)
- 复盘：[`docs/05-retrospective.md`](docs/05-retrospective.md)
- 本人运行与复核记录：[`docs/06-personal-review.md`](docs/06-personal-review.md)
- 合成制度资料：[`data/policies.json`](data/policies.json)
- 测试：`uv run python -m unittest discover -s tests`

依赖及 Python 版本约束写在 `pyproject.toml`，具体版本写在 `uv.lock`；两者应提交到 Git。`.env`、`.venv/`、构建缓存和 `*.egg-info/` 由 `.gitignore` 排除。密钥只放在本地 `.env`，不要写进 `pyproject.toml`、运行命令或 Trace。

## 当前边界

- 资料是为考核编写的合成示例，不包含真实企业制度或隐私信息。
- 检索使用轻量关键词/字符二元组匹配，不等同于生产级语义检索。
- 真实模式需要可用的模型密钥和支持工具调用的模型；正常、冲突追问、上下文追问、相似改写、资料不足、工具失败和调用上限场景均有实际记录，索引见 `examples/README.md`。
- 默认每轮最多执行 4 次工具调用；触顶时 Trace 标记 `incomplete`。
- 轻量检索包含少量显式业务同义词，仅用于合成资料演示。
