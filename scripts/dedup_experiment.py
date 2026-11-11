"""A＋去重 experiment bookkeeping; no model calls in retrieval stage."""
import argparse
import importlib.util
import json
from pathlib import Path
from agent_baseline import ROOT, BASELINE, sha, write, git, config
from retrieval_baseline import measure, aggregate

EXPERIMENT = ROOT / "examples/evaluation/a_plus_dedup/20261110_v020"


def freeze():
    EXPERIMENT.mkdir(parents=True, exist_ok=False)
    paths = list((ROOT / "src").rglob("*.py")) + list(BASELINE.rglob("*")) + list((ROOT / "examples/evaluation/agent_baseline/20261110_original_agent_v020").rglob("*"))
    protected = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in paths if p.is_file()}
    write(EXPERIMENT / "before.json", {"name": "A＋去重", "commit": git("rev-parse", "HEAD"),
          "status": git("status", "--porcelain=v1", "--untracked-files=all"),
          "diff": git("diff", "HEAD", "--name-status"), "hashes": protected, "model_config": config()})


def retrieval(output=None):
    output = output or EXPERIMENT
    output.mkdir(parents=True, exist_ok=True)
    before = json.loads((EXPERIMENT / "before.json").read_text(encoding="utf-8"))
    for path, value in before["hashes"].items():
        if path != "src/enterprise_qa_agent/knowledge.py":
            assert sha(ROOT / path) == value, path
    spec = importlib.util.spec_from_file_location("actual_knowledge", ROOT / "src/enterprise_qa_agent/knowledge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gold = json.loads((BASELINE / "gold.json").read_text(encoding="utf-8"))
    old = {(r["case_id"], r["k"]): r for line in (BASELINE / "results.jsonl").read_text(encoding="utf-8").splitlines() if (r := json.loads(line))}
    rows = []
    for case in gold["cases"]:
        assert sha(ROOT / case["corpus"]) == case["corpus_sha256"]
        for k in [1, 3, 5, 10]:
            from time import perf_counter_ns
            kb = module.KnowledgeBase(ROOT / case["corpus"])
            start = perf_counter_ns()
            hits = kb.search(case["original_query"], k)
            elapsed = (perf_counter_ns() - start) / 1e6
            metrics = measure(case, hits)
            previous = old[(case["case_id"], k)]
            rows.append({"case_id": case["case_id"], "k": k, "query": case["original_query"],
                "corpus": case["corpus"], "corpus_sha256": case["corpus_sha256"],
                "category": case["category"], "business_answer_kind": case["business_answer_kind"],
                "candidates": [{**h, "rank": i} for i, h in enumerate(hits, 1)], "search_elapsed_ms": elapsed,
                "metrics": metrics, "before_metrics": previous["metrics"],
                "candidate_changed": hits != [{key: val for key, val in h.items() if key not in {"rank", "corpus_metadata"}} for h in previous["candidates"]],
                "recall_degraded": metrics["recall"] is not None and metrics["recall"] < previous["metrics"]["recall"]})
    with (output / "retrieval_results.jsonl").open("x", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    write(output / "retrieval_metrics.json", {str(k): aggregate([r for r in rows if r["k"] == k]) for k in [1, 3, 5, 10]})
    write(output / "retrieval_manifest.json", {"name": "A＋去重", "gold_sha256": sha(BASELINE / "gold.json"),
          "source_sha256": sha(ROOT / "src/enterprise_qa_agent/knowledge.py"), "rows": len(rows),
          "regressions": [f"{r['case_id']}@{r['k']}" for r in rows if r["recall_degraded"]]})
    print((output / "retrieval_metrics.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["freeze", "retrieval"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze()
    else:
        retrieval(args.output)
