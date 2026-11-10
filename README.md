# 企业制度问答 Agent（v0.2.0）

单 Agent + 本地制度检索工具的 CLI 示例。真实模式使用 AgentScope 2.0.11 的 `Agent` + `ReActConfig`，由模型选择 `search_docs` / `read_doc` 工具；离线模式仅用于检查检索与输出流程，不代表模型决策效果。

## 环境与运行

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
- 合成制度资料：[`data/policies.json`](data/policies.json)
- 测试：`uv run python -m unittest discover -s tests`

依赖及 Python 版本约束写在 `pyproject.toml`，具体版本写在 `uv.lock`；两者应提交到 Git。`.env`、`.venv/`、构建缓存和 `*.egg-info/` 由 `.gitignore` 排除。密钥只放在本地 `.env`，不要写进 `pyproject.toml`、运行命令或 Trace。

## 当前边界

- 资料是为考核编写的合成示例，不包含真实企业制度或隐私信息。
- 检索使用轻量关键词/字符二元组匹配，不等同于生产级语义检索。
- 真实模式需要可用的模型密钥和支持工具调用的模型；正常、冲突追问、上下文追问、相似改写、资料不足、工具失败和调用上限场景均有实际记录，索引见 `examples/README.md`。
- 默认每轮最多执行 4 次工具调用；触顶时 Trace 标记 `incomplete`。
- 轻量检索包含少量显式业务同义词，仅用于合成资料演示。
