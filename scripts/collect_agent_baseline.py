"""Collect original CLI traces without further retrieval or model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from agent_baseline import BASELINE, check, read, rel, sha, write


def key(item):
    return f"{item['doc_id']}/{item['section_id']}"


def evidence(payload):
    found = []
    for item in payload.get("results", []):
        found.append(dict(item))
    document = payload.get("document")
    if document:
        for section in document.get("sections", []):
            found.append({**{k: v for k, v in document.items() if k != "sections"}, **section})
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    check(folder)
    plan = read(folder / "plan.json")
    gold = {c["case_id"]: c for c in read(BASELINE / "gold.json")["cases"]}
    baseline = {r["case_id"]: r for line in (BASELINE / "results.jsonl").read_text(encoding="utf-8").splitlines()
                if (r := json.loads(line))["k"] == 5}
    rows = []
    for item in plan["runs"]:
        case = next(c for c in plan["cases"] if c["case_id"] == item["case_id"])
        session = folder / "sessions" / item["run_id"]
        traces = list((session / "traces").glob("*.json"))
        launcher = read(folder / "launcher" / f"{item['run_id']}.json")
        execution = read(session / "execution.json") if (session / "execution.json").exists() else None
        replies = read(session / "reply_metadata.json") if (session / "reply_metadata.json").exists() else []
        returns = read(session / "tool_returns.json") if (session / "tool_returns.json").exists() else []
        trace = read(traces[0]) if len(traces) == 1 else None
        required = {key(e) for e in case["necessary_evidence"]}
        steps, first, visible = [], None, {}
        if trace:
            assert trace["mode"] == "agentscope_react" and trace["tool_call_limit"] == 4
            assert trace["corpus"]["sha256"] == case["corpus_sha256"]
            slots = [e for e in trace["events"] if e["type"] in {"tool_call", "limit"}]
            assert len(slots) == len(returns), f"Missing full tool returns: {item['run_id']}"
            for slot, returned in zip(slots, returns):
                payload = returned["payload_passed_to_original_tool_response"]
                parsed = json.loads(returned["returned_tool_response"]["content"][0]["text"])
                assert parsed == payload
                observed = evidence(parsed)
                visible_keys = {key(e) for e in observed}
                if first is None and slot["tool"] == "search_docs":
                    first = visible_keys
                for ev in observed:
                    visible.setdefault(key(ev), []).append({"turn": slot["turn"], "step": slot["step"],
                                                           "tool": slot["tool"], "visible_evidence": ev})
                steps.append({"turn": slot["turn"], "step": slot["step"], "tool": slot["tool"],
                              "executed": slot["type"] == "tool_call", "arguments": slot["arguments"],
                              "public_decision_reason": slot.get("public_decision_reason"),
                              "full_tool_return": parsed,
                              "returned_response": returned["returned_tool_response"],
                              "visible_keys": sorted(visible_keys), "error": parsed.get("error")})
            assert all(sum(e["type"] == "tool_call" and e["turn"] == turn for e in trace["events"]) <= 4
                       for turn in {e.get("turn") for e in trace["events"]})
        raw = baseline.get(case["case_id"])
        raw_matched = set(raw["metrics"]["matched"]) if raw else None
        complete = required <= set(visible) if required else None
        first_complete = required <= (first or set()) if required else None
        quotes = re.findall(r"[“「]([^”」]+)[”」]", trace["answer"]) if trace else []
        rows.append({
            "run_id": item["run_id"], "case_id": case["case_id"], "repeat": item["repeat"],
            "messages": case["messages"], "corpus": case["corpus"], "corpus_sha256": case["corpus_sha256"],
            "trace_path": rel(traces[0]) if trace else None, "trace_sha256": sha(traces[0]) if trace else None,
            "execution": execution, "launcher": launcher,
            "execution_status": trace["status"] if trace else "no_trace",
            "model_reply_metadata": replies,
            "tool_calls": trace["tool_calls"] if trace else None,
            "tool_steps": steps, "actually_visible_evidence": visible,
            "necessary_evidence_keys": sorted(required), "missing_necessary_evidence": sorted(required - set(visible)),
            "baseline_raw_query_k5_necessary_hit": sorted(raw_matched) if raw_matched is not None else None,
            "first_agent_search_necessary_hit": sorted(required & (first or set())),
            "first_agent_search_complete": first_complete, "all_visible_complete": complete,
            "recovered_vs_raw_query_k5": bool(complete and not required <= raw_matched) if required and raw_matched is not None else None,
            "recovered_after_agent_first_search": bool(complete and not first_complete) if required else None,
            "budget_rejected_requests": [e for e in steps if not e["executed"]],
            "final_answer": trace["answer"] if trace else None,
            "conversation": trace.get("conversation") if trace else None,
            "mentioned_ids_not_automatically_claim_citations": sorted(set(re.findall(r"\b(?:D\d+|COPY\d+)(?:-S\d+)?\b", trace["answer"]))) if trace else [],
            "quote_spans_for_manual_check": quotes,
            "manual_review": None,
        })
    with (folder / "observations.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    write(folder / "collection_manifest.json", {"collector_sha256": sha(__file__), "observations_sha256": sha(folder / "observations.jsonl"),
          "session_count": len(rows), "all_protected_files_unchanged": True,
          "note": "All visible evidence comes solely from actual tool-return payloads; corpus gold never supplied to model"})
    for row in rows:
        print(json.dumps({k: row[k] for k in ["run_id", "execution_status", "tool_calls", "missing_necessary_evidence", "recovered_vs_raw_query_k5", "recovered_after_agent_first_search"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
