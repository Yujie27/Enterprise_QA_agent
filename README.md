# 企业制度问答 Agent（最小可运行版）

单 Agent + 本地制度检索工具的 CLI 示例。真实模式使用 AgentScope 2.0.11 的 `Agent` + `ReActConfig`，由模型选择 `search_docs` / `read_doc` 工具；离线模式仅用于检查检索与输出流程，不代表模型决策效果。

## 环境与运行

要求 Python 3.11+。

```powershell
cd C:\Users\ZONST\Desktop\Enterprise_QA_agent
uv sync
Copy-Item .env.example .env
```

编辑 `.env`，填写模型 API 配置后运行真实 Agent：

```powershell
uv run enterprise-qa "报销期限是几天？"
```

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
- 真实模式需要可用的模型密钥和支持工具调用的模型；已有一条正常场景真实运行记录，见 `examples/runs/20261109_171637_918335.json`，其余验收场景仍需补齐。
- 默认最多执行 4 次工具调用；触顶时 Trace 标记未完成。
