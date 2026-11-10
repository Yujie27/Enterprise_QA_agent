"""CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .agent import RunRecorder, build_agent
from .knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[2]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts) if parts else str(content)
    return str(content)


def _task_status(recorder: RunRecorder) -> str:
    if recorder.limit_reached:
        return "incomplete"
    summaries = [
        event.get("summary", "")
        for event in recorder.events
        if event.get("type") == "tool_result"
    ]
    if any("工具失败" in summary for summary in summaries):
        return "tool_error"
    if summaries and all("没有检索到匹配资料" in summary for summary in summaries):
        return "insufficient_evidence"
    return "completed"


def _run_mock(question: str, corpus: KnowledgeBase, recorder: RunRecorder) -> tuple[str, str]:
    """Scripted offline plumbing demo; deliberately not a model-decision claim."""
    recorder.events.append(
        {"type": "notice", "summary": "SCRIPTED MOCK：以下动作预设，仅验证本地工具链，不代表模型决策。"}
    )
    query = "报销 期限" if "报销" in question else question
    if recorder.begin_tool("search_docs", {"query": query, "limit": 5}):
        results = corpus.search(query, 5)
        recorder.finish_tool("search_docs", f"返回 {len(results)} 条资料")
    else:
        results = []
    docs = []
    for hit in results[:2]:
        if recorder.begin_tool("read_doc", {"doc_id": hit["doc_id"]}):
            doc = corpus.read(hit["doc_id"])
            recorder.finish_tool("read_doc", "已读取文档原文" if doc else "文档不存在")
            if doc:
                docs.append(doc)
    if not results:
        return "mock_incomplete", "离线 Mock 未找到资料；请配置真实模型后运行，以观察模型是否选择改写查询或追问。"
    unique_ids = sorted({d["doc_id"] for d in docs})
    if len(unique_ids) > 1:
        answer = "检索到多份可能相关制度，规则可能因适用范围不同而冲突。请补充所在部门或报销类型，我再判断适用条款。引用：" + ", ".join(unique_ids)
    else:
        answer = "离线 Mock 已检索并读取相关资料。请查看 Trace 中的原文与适用范围；该输出不是模型生成答案。引用：" + ", ".join(unique_ids)
    return "mock_completed", answer


async def _run_real(
    question: str,
    corpus: KnowledgeBase,
    recorder: RunRecorder,
    simulate_failure: str | None = None,
) -> tuple[str, str]:
    from agentscope.message import UserMsg

    event_start = recorder.start_turn(question)
    agent = build_agent(corpus, recorder, simulate_failure=simulate_failure)
    response = await agent.reply(UserMsg(name="user", content=question))
    text = response.get_text_content() or _content_to_text(response.content)
    recorder.finish_turn(event_start, text)
    if recorder.limit_reached:
        return "incomplete", f"未完成：达到工具调用上限（{recorder.max_tool_calls}）。\n{text}"
    return _task_status(recorder), text


async def _run_interactive(
    initial_question: str,
    follow_ups: list[str],
    corpus: KnowledgeBase,
    recorder: RunRecorder,
    simulate_failure: str | None,
) -> tuple[str, str, list[dict[str, str]]]:
    from agentscope.message import UserMsg

    agent = build_agent(corpus, recorder, simulate_failure=simulate_failure)
    conversation: list[dict[str, str]] = []
    pending = initial_question
    queued_follow_ups = list(follow_ups)
    scripted = bool(follow_ups)
    print("交互模式已启动，输入 /exit 结束。")
    while True:
        if pending:
            question = pending
        elif queued_follow_ups:
            question = queued_follow_ups.pop(0)
            print(f"你：{question}")
        elif scripted:
            break
        else:
            question = input("你：").strip()
        pending = ""
        if question.lower() in {"/exit", "/quit", "exit", "quit"}:
            break
        if not question:
            continue
        event_start = recorder.start_turn(question)
        response = await agent.reply(UserMsg(name="user", content=question))
        answer = response.get_text_content() or _content_to_text(response.content)
        recorder.finish_turn(event_start, answer)
        conversation.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
        )
        print(f"Agent：{answer}")
        if recorder.limit_reached:
            print(f"本轮已达到工具调用上限（{recorder.max_tool_calls}）。")
    status = _task_status(recorder)
    answer = conversation[-1]["content"] if conversation else "未进行对话。"
    return status, answer, conversation


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="企业制度问答 Agent")
    parser.add_argument("question", nargs="*", help="要查询的制度问题")
    parser.add_argument("--mock", action="store_true", help="离线流程演示，不代表模型决策")
    parser.add_argument("--interactive", action="store_true", help="多轮交互模式；输入 /exit 结束")
    parser.add_argument(
        "--follow-up",
        action="append",
        default=[],
        help="交互模式的后续消息；可重复传入，便于复现多轮验收",
    )
    parser.add_argument(
        "--simulate-failure",
        choices=["search_docs", "read_doc"],
        help="仅用于验收：模拟指定工具失败，让模型观察错误并调整动作",
    )
    parser.add_argument("--corpus", default=str(ROOT / "data" / "policies.json"))
    parser.add_argument("--trace-dir", default=str(ROOT / "examples" / "runs"))
    args = parser.parse_args()
    question = " ".join(args.question).strip()
    if not question and not args.interactive:
        parser.error("请提供问题，例如：enterprise-qa '报销期限是几天？'")
    if args.mock and args.interactive:
        parser.error("--mock 与 --interactive 不能同时使用")
    if args.follow_up and not args.interactive:
        parser.error("--follow-up 必须与 --interactive 一起使用")
    if args.mock and args.simulate_failure:
        parser.error("--simulate-failure 只用于真实模型模式")

    max_calls = int(os.getenv("MAX_TOOL_CALLS", "4"))
    if max_calls < 1:
        parser.error("MAX_TOOL_CALLS 必须大于 0")
    corpus = KnowledgeBase(args.corpus)
    recorder = RunRecorder(max_calls)
    conversation: list[dict[str, str]] | None = None

    try:
        if args.mock:
            recorder.start_turn(question)
            status, answer = _run_mock(question, corpus, recorder)
            recorder.finish_turn(1, answer)
        elif args.interactive:
            status, answer, conversation = asyncio.run(
                _run_interactive(question, args.follow_up, corpus, recorder, args.simulate_failure)
            )
        else:
            status, answer = asyncio.run(
                _run_real(question, corpus, recorder, args.simulate_failure)
            )
    except Exception as exc:
        status, answer = "failed", f"运行失败：{type(exc).__name__}: {exc}"

    trace = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "scripted_mock" if args.mock else "agentscope_react",
        "question": question,
        "status": status,
        "tool_call_limit": max_calls,
        "tool_calls": recorder.tool_calls,
        "events": recorder.events,
        "answer": answer,
    }
    if conversation is not None:
        trace["conversation"] = conversation
    if args.simulate_failure:
        trace["simulated_failure"] = args.simulate_failure
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json")
    trace_json = json.dumps(trace, ensure_ascii=False, indent=2)
    trace_path.write_bytes(trace_json.encode("utf-8", errors="replace"))
    print(f"状态：{status}")
    print(answer)
    print(f"Trace：{trace_path}")


if __name__ == "__main__":
    main()
