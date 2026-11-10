# 04 AI 辅助使用与个人贡献

## AI 辅助范围

本仓库使用 Codex 辅助生成最小项目骨架、合成资料、AgentScope 工具接入、CLI、测试和文档，并辅助定位 AgentScope 版本 API 不兼容问题。后续的多轮上下文、同义词归一化、故障注入、状态分类和 Trace 增强也由 AI 辅助实现。

## 候选人贡献与核验

- 选择企业制度问答题目，确定单 Agent、CLI 和合成资料的最小范围。
- 提供本地模型配置，实际运行并审阅命令、答案、Trace 与 Git 提交内容。
- 根据真实运行暴露的问题确认修改方向，包括 AgentScope 2.0.11 API 适配、无结果停止规则和验收场景补齐。
- 不提交密钥、真实制度或隐私数据。

## 验证方式

- 执行 `uv run python -m unittest discover -s tests`，2026-11-10 共 8 个测试通过。
- 使用真实模型运行正常、冲突追问、多轮上下文、相似问法、资料不足和工具失败场景；实际输出和 Trace 保存在 `examples/runs/`。
- Mock 记录明确标记为 `scripted_mock`，不作为真实模型决策证据。

## 第三方组件

依赖由 `pyproject.toml` 声明：AgentScope 2.0.11、python-dotenv。当前未复制第三方项目源代码。
