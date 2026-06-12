# 研发文档与实验日志智能助手 Demo

轻量 RAG/Agent 工程 Demo，面向研发文档、实验记录与运行日志。

## 功能

- 文档问答：检索 `demo_data/docs` 中的文档并返回引用片段
- 日志检索：检索 `demo_data/logs` 中的训练日志、对打日志、服务日志
- 实验查询：读取 `demo_data/experiments.csv`，查询实验指标
- 简单任务路由：根据问题自动路由到文档问答、日志检索、实验查询或总结
- 可选 LLM：默认本地抽取式回答；配置 OpenAI 兼容 API 后可生成更自然的总结

## 快速启动

```bash
cd rag_agent_demo
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/build_index.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

## 接口示例

```bash
curl -X POST http://127.0.0.1:8000/ingest

curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"这个项目的主要难点是什么？","top_k":4}'

curl -X POST http://127.0.0.1:8000/search_logs \
  -H "Content-Type: application/json" \
  -d '{"query":"win rate 提升但 avg score 下降","top_k":5}'

curl -X POST http://127.0.0.1:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{"query":"best win_rate","top_k":5}'

curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"question":"总结最近实验中效果不稳定的主要原因","top_k":5}'
```

## 可选：接入 OpenAI 兼容 API

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=你的key
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o-mini
```

## 面试讲法

这个项目可以这样讲：

> 我做了一个面向研发场景的轻量 RAG/Agent Demo，围绕研发文档、实验记录和运行日志，支持文档问答、日志检索、实验查询和总结生成。系统默认采用本地 TF-IDF 与关键词混合检索，并返回引用片段；同时预留 OpenAI 兼容接口，可以接入大模型生成更自然的总结。项目重点不是单纯聊天，而是解决研发过程中查文档、查日志、对比实验和复盘问题的效率问题。

## 注意

演示数据全部是脱敏样例，不包含公司代码、真实日志或未公开专利内容。
