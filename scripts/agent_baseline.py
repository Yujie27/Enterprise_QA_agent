"""Run the unchanged real CLI with passive output observers, never rewrite queries.

prepare freezes sources, previous evaluation and criteria. run creates isolated
subprocesses (2 at a time) and never retries a scenario beyond the fixed plan.
worker invokes the ORIGINAL cli.main; observers return original objects unchanged.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from time import perf_counter
import traceback
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "examples/evaluation/retrieval_baseline/20261110_raw_query_v020"
IDS = ["R01", "R06", "R07", "C01", "C02", "C05", "C11", "C12", "C13", "M01", "E03", "F01"]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def config():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from agentscope.model import OpenAIChatModel
    url = urlsplit(os.getenv("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1")
    # Never save credentials, URL query parameters, userinfo, custom headers or env contents.
    endpoint = f"{url.scheme}://{url.hostname or ''}" + (f":{url.port}" if url.port else "")
    parameters = OpenAIChatModel.Parameters(parallel_tool_calls=False).model_dump(mode="json")
    return {
        "model": os.getenv("OPENAI_MODEL", "").strip(),
        "endpoint_origin": endpoint,
        "endpoint_path": "/v1" if url.path in {"", "/v1", "/v1/"} else "[custom path omitted]",
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "stream": False, "parameters": parameters,
        "sampling_note": "temperature/top_p/seed not explicitly set by original code; provider defaults apply",
        "tool_budget_per_turn": 4,
        "configured_budget_before_runner": os.getenv("MAX_TOOL_CALLS", "4"),
        "react_max_iters": 5, "model_max_retries_default": 3, "model_retry_delay_default": 1.0,
        "versions": {p: importlib.metadata.version(p) for p in ["agentscope", "openai", "python-dotenv", "enterprise-qa-agent-minimal"]},
    }


def redact(text):
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        text = text.replace(key, "[API_KEY_REDACTED]")
    return text


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=False)
    cases = read(BASELINE / "input/qa_boundary_test_design/cases.json")["cases"]
    design = {c["id"]: c for c in cases}
    gold = {c["case_id"]: c for c in read(BASELINE / "gold.json")["cases"]}
    records = []
    for case_id in IDS:
        case = design[case_id]
        evidence = gold.get(case_id, {}).get("necessary_evidence", [])
        if case_id == "M01":
            evidence = [{"doc_id": "D02", "section_id": "D02-S1"}]
        elif case_id == "E03":
            evidence = [{"doc_id": "D01", "section_id": "D01-S1"}]
        corpus = BASELINE / "input/qa_boundary_test_design" / case["corpus"]
        records.append({
            "case_id": case_id, "messages": case["messages"],
            "corpus": rel(corpus), "corpus_sha256": sha(corpus),
            "necessary_evidence": evidence,
            "baseline_raw_query_k5": rel(BASELINE / "results.jsonl") if case_id in gold else None,
            "expected": case["expected"], "setup": case["setup"],
            "simulate_failure": "search_docs" if case_id == "F01" else None,
        })
    runs = [{"run_id": f"{c}_r1", "case_id": c, "repeat": 1, "batch": "primary"} for c in IDS]
    runs += [{"run_id": f"{c}_r{n}", "case_id": c, "repeat": n, "batch": "repeats"}
             for c in ["C01", "C11", "C13"] for n in [2, 3]]
    criteria = {
        "scope": "original real CLI, no manual rewrite, no evidence supplied to model beyond original tools",
        "strict_business_pass": "Correct source-bounded main conclusion, supported citations, required gaps explicit, no unsupported policy assertion or execution advice; budget/framework failure tracked separately",
        "recovery_axes": ["raw_query_k5_vs_agent_visible_evidence", "agent_first_search_vs_later_observations"],
        "labels": ["必要证据未召回，模型未恢复", "首次未召回，但模型通过后续动作恢复", "必要证据已可见，模型仍判断错误", "主答案正确，但引用错误或附带无依据断言", "工程异常、预算不足或路径未触发"],
        "R07": "Check visible scope and publicly stated scope-based explanation; no order/ID counterfactual, so cannot causally prove independence from ranking",
        "E03": "Do not choose natural/work days or recommend one as an execution rule without evidence",
        "C13": "Assess visible30day+15day claims, count copies once; never treat hidden corpus sections or copied_from metadata absent from actual search as model-visible",
        "M01": "Same original CLI interactive session, exact two design messages; check per-turn evidence and final context use",
        "F01": "Use original search failure switch; if agent truly recovers using another working tool, report actual recovery rather than inventing failure",
        "observer": "Passive wrappers of _tool_response and Agent.reply record ORIGINAL returned objects and metadata, then return them unchanged; no tool replacement/retrieval override",
        "repeat_policy": "1 per case plus2 for C01/C11/C13; no success selection; max concurrency2 independent processes; CLI errors preserved; external900s watchdog separate from tool budget",
        "B1_working_definition": "query/initial retrieval evidence acquisition improvements; not implemented in this run",
        "B2_working_definition": "related/conflicting evidence supplementation, source diversity and evidence-aware decision/answer control; not implemented in this run",
    }
    write(folder / "plan.json", {"prepared_at_utc": now(), "cases": records, "runs": runs, "criteria": criteria})
    protected = {}
    for base in [ROOT / "src", ROOT / "data", BASELINE]:
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protected[rel(p)] = sha(p)
    for p in [ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "README.md"]:
        protected[rel(p)] = sha(p)
    manifest = {
        "prepared_at_utc": now(), "branch": git("branch", "--show-current"),
        "commit_sha": git("rev-parse", "HEAD"),
        "existing_worktree_status": git("status", "--porcelain=v1", "--untracked-files=all"),
        "tracked_diff": git("diff", "HEAD", "--name-status"),
        "tracked_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)).hexdigest(),
        "model_config": config(), "python": platform.python_version(),
        "protected_file_sha256": protected,
        "plan_sha256": sha(folder / "plan.json"),
        "runner_sha256": sha(__file__),
        "previous_gold_sha256": sha(BASELINE / "gold.json"),
        "case_count": 12, "session_count": 18, "user_turn_count": 19,
        "no_mock": True, "concurrency": 2,
    }
    write(folder / "manifest.json", manifest)
    print(json.dumps({"prepared": 18, "model_config": manifest["model_config"]}, ensure_ascii=False))


def check(folder):
    manifest = read(folder / "manifest.json")
    assert manifest["plan_sha256"] == sha(folder / "plan.json")
    assert manifest["runner_sha256"] == sha(__file__), "Runner changed after prepare"
    for path, value in manifest["protected_file_sha256"].items():
        assert sha(ROOT / path) == value, f"Protected code or previous baseline changed: {path}"
    assert config() == manifest["model_config"], "Model configuration changed"
    return manifest


def worker(folder, run_id):
    manifest = check(folder)
    plan = read(folder / "plan.json")
    item = next(r for r in plan["runs"] if r["run_id"] == run_id)
    case = next(c for c in plan["cases"] if c["case_id"] == item["case_id"])
    session = folder / "sessions" / run_id
    session.mkdir(parents=True, exist_ok=False)
    started = now()
    if not manifest["model_config"]["api_key_configured"] or not manifest["model_config"]["model"]:
        write(session / "execution.json", {"run_id": run_id, "execution": "not_executed", "reason": "model configuration unavailable", "started_at_utc": started})
        return
    os.environ["MAX_TOOL_CALLS"] = "4"
    sys.path.insert(0, str(ROOT / "src"))
    from enterprise_qa_agent import agent as wiring
    from enterprise_qa_agent import cli
    from agentscope.agent import Agent
    tool_returns, replies = [], []
    original_response = wiring._tool_response
    original_reply = Agent.reply

    def observe_response(payload):
        response = original_response(payload)
        tool_returns.append({"index": len(tool_returns) + 1, "timestamp_utc": now(),
                             "payload_passed_to_original_tool_response": payload,
                             "returned_tool_response": response.model_dump(mode="json")})
        return response

    async def observe_reply(self, *args, **kwargs):
        response = await original_reply(self, *args, **kwargs)
        replies.append({"turn": len(replies) + 1, "finished_reason": str(response.finished_reason),
                        "usage": response.usage.model_dump(mode="json") if response.usage else None,
                        "error": response.error.model_dump(mode="json") if response.error else None,
                        "text": response.get_text_content()})
        return response

    wiring._tool_response = observe_response
    Agent.reply = observe_reply
    trace_dir = session / "traces"
    sys.argv = ["enterprise-qa", "--corpus", str(ROOT / case["corpus"]), "--trace-dir", str(trace_dir)]
    if case["simulate_failure"]:
        sys.argv += ["--simulate-failure", case["simulate_failure"]]
    if len(case["messages"]) > 1:
        sys.argv += ["--interactive"]
        for message in case["messages"][1:]:
            sys.argv += ["--follow-up", message["content"]]
    sys.argv += [case["messages"][0]["content"]]
    error = None
    timer = perf_counter()
    try:
        cli.main()
    except BaseException as exc:
        error = redact(f"{type(exc).__name__}: {exc}")
    finally:
        wiring._tool_response = original_response
        Agent.reply = original_reply
        # Exclude private ThinkingBlocks: only tool results and public final text saved.
        write(session / "tool_returns.json", json.loads(redact(json.dumps(tool_returns, ensure_ascii=False))))
        write(session / "reply_metadata.json", json.loads(redact(json.dumps(replies, ensure_ascii=False))))
        write(session / "execution.json", {"run_id": run_id, "case_id": case["case_id"], "repeat": item["repeat"],
              "execution": "attempted", "started_at_utc": started, "finished_at_utc": now(),
              "elapsed_seconds": perf_counter() - timer, "uncaught_error": error,
              "cli_args": sys.argv, "model_config": manifest["model_config"],
              "corpus_sha256": sha(ROOT / case["corpus"]), "tool_return_count": len(tool_returns)})


def run_batch(folder, batch):
    check(folder)
    plan = read(folder / "plan.json")
    runs = [r for r in plan["runs"] if r["batch"] == batch]
    if any((folder / "sessions" / r["run_id"]).exists() for r in runs):
        raise RuntimeError("A planned session exists; refusing to rerun or overwrite")
    launcher = folder / "launcher"
    launcher.mkdir(exist_ok=True)

    def launch(item):
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "worker", "--run-dir", str(folder), "--run-id", item["run_id"]]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        started = now()
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=900)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code, timed_out = exc.stdout or b"", exc.stderr or b"", None, True
        for label, value in [("stdout", stdout), ("stderr", stderr)]:
            text = redact(value.decode("utf-8", errors="replace"))
            with (launcher / f"{item['run_id']}.{label}.txt").open("x", encoding="utf-8") as stream:
                stream.write(text)
        write(launcher / f"{item['run_id']}.json", {"run_id": item["run_id"], "started_at_utc": started,
              "finished_at_utc": now(), "returncode": code, "watchdog_timeout": timed_out})
        traces = list((folder / "sessions" / item["run_id"] / "traces").glob("*.json"))
        trace = read(traces[0]) if len(traces) == 1 else {}
        print(json.dumps({"run_id": item["run_id"], "trace_status": trace.get("status", "no_trace"),
                          "tool_calls": trace.get("tool_calls"), "watchdog_timeout": timed_out}, ensure_ascii=False), flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(launch, r) for r in runs]
        for future in as_completed(futures):
            future.result()
    check(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "run", "worker"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--batch", choices=["primary", "repeats"])
    parser.add_argument("--run-id")
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    if args.stage == "prepare":
        prepare(folder)
    elif args.stage == "run":
        assert args.batch
        run_batch(folder, args.batch)
    else:
        assert args.run_id
        worker(folder, args.run_id)


if __name__ == "__main__":
    main()
