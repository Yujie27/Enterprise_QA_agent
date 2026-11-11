"""Isolated B / dedup+B runner. All trials use the frozen original case plan."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import agent_baseline as base

ROOT = base.ROOT
OUT = ROOT / "examples/evaluation/demand_rewrite/20261110_v020"


def seal():
    OUT.mkdir(parents=True, exist_ok=False)
    snapshot = OUT / "sealed_a_dedup"
    snapshot.mkdir()
    files = list((ROOT / "src").rglob("*.py"))
    hashes = {}
    for path in files:
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        hashes[base.rel(path)] = base.sha(path)
    history = {}
    for folder in [ROOT / "examples/evaluation/a_plus_dedup", base.BASELINE, ROOT / "examples/evaluation/agent_baseline"]:
        for path in folder.rglob("*"):
            if path.is_file():
                history[base.rel(path)] = base.sha(path)
    diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    (snapshot / "worktree.patch").write_bytes(diff)
    base.write(OUT / "before.json", dict(commit=base.git("rev-parse", "HEAD"), branch=base.git("branch", "--show-current"),
               worktree=base.git("status", "--porcelain=v1", "--untracked-files=all"), source_hashes=hashes,
               historical_hashes=history, model_config=base.config()))


def worker(folder, run_id, mode):
    sys.path.insert(0, str(ROOT / "src"))
    from enterprise_qa_agent import cli
    original = cli.main
    def configured():
        sys.argv += ["--retrieval-mode", mode, "--demand-rewrite"]
        original()
    cli.main = configured
    base.worker(folder, run_id)


def batch(folder, batch_name, mode):
    base.check(folder)
    runs = [r for r in base.read(folder / "plan.json")["runs"] if r["batch"] == batch_name]
    logs = folder / "launcher"
    logs.mkdir(exist_ok=True)
    def launch(item):
        assert not (folder / "sessions" / item["run_id"]).exists()
        result = subprocess.run([sys.executable, "-B", __file__, "worker", "--folder", str(folder), "--mode", mode, "--run-id", item["run_id"]],
                                cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"), capture_output=True, timeout=900)
        for label, content in [("stdout", result.stdout), ("stderr", result.stderr)]:
            (logs / f"{item['run_id']}.{label}.txt").write_text(base.redact(content.decode("utf-8", errors="replace")), encoding="utf-8")
        base.write(logs / f"{item['run_id']}.json", dict(run_id=item["run_id"], returncode=result.returncode, watchdog_timeout=False))
        traces = list((folder / "sessions" / item["run_id"] / "traces").glob("*.json"))
        trace = base.read(traces[0]) if traces else {}
        print(item["run_id"], trace.get("status", "no_trace"), trace.get("tool_calls"), flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(launch, runs))
    base.check(folder)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["seal", "prepare", "worker", "run"])
    p.add_argument("--folder", type=Path)
    p.add_argument("--mode", choices=["original", "dedup"])
    p.add_argument("--batch", default="primary")
    p.add_argument("--run-id")
    a = p.parse_args()
    if a.stage == "seal":
        seal()
    elif a.stage == "prepare":
        base.prepare(a.folder)
        base.write(a.folder / "experiment_config.json", dict(name="B=A＋按需改写" if a.mode == "original" else "去重＋按需改写", retrieval_mode=a.mode, demand_rewrite=True, tool_budget=4))
    elif a.stage == "worker":
        worker(a.folder, a.run_id, a.mode)
    else:
        batch(a.folder, a.batch, a.mode)
