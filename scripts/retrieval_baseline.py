"""Offline, read-only retrieval measurement. No Agent, model, dotenv or network.

Freeze annotations in a separate invocation BEFORE run. Existing output files are
never overwritten. All diagnostic reconstructions are labelled, not retrievals.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter_ns


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/enterprise_qa_agent/knowledge.py"
KS = (1, 3, 5, 10)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def snapshot():
    tracked = git("ls-files", "-z").split("\0")
    # Exclude secrets even if a future checkout accidentally tracks one.
    protected = [p for p in tracked if p and not any(
        part.startswith(".env") and part != ".env.example"
        or part == ".venv" for part in Path(p).parts
    )]
    return {
        "branch": git("branch", "--show-current"),
        "commit_sha": git("rev-parse", "HEAD"),
        "status_porcelain": git("status", "--porcelain=v1", "--untracked-files=all"),
        "tracked_changes": git("diff", "HEAD", "--name-status"),
        "tracked_file_sha256": {
            p: digest(ROOT / p) if (ROOT / p).is_file() else None for p in protected
        },
    }


def evidence_key(value):
    if isinstance(value, str):
        return value
    return f"{value['doc_id']}/{value['section_id']}"


def sections(docs):
    return {
        f"{doc['doc_id']}/{section['section_id']}": (doc, section)
        for doc in docs for section in doc.get("sections", [])
    }


def freeze(args):
    folder = args.run_dir.resolve()
    design_root = folder / "input/qa_boundary_test_design"
    import zipfile
    with zipfile.ZipFile(args.archive) as archive:
        for entry in archive.infolist():
            if not entry.is_dir():
                assert (folder / "input" / entry.filename).read_bytes() == archive.read(entry), "Archive extraction differs"
    design = read_json(design_root / "cases.json")
    specification = read_json(args.spec)
    cases = {case["id"]: case for case in design["cases"]}
    selected = specification["selected_cases"]
    selected_ids = [item["case_id"] for item in selected]
    assert len(cases) == 60 and len(selected_ids) == len(set(selected_ids)) == 27
    assert set(cases) == set(selected_ids) | set(specification["not_executed_case_ids"])
    assert set(specification["excluded_case_ids"]) <= set(selected_ids)
    records = []
    for item in selected:
        case = cases[item["case_id"]]
        corpus = design_root / case["corpus"]
        docs = read_json(corpus)
        indexed = sections(docs)
        assert len(indexed) == sum(len(doc.get("sections", [])) for doc in docs)

        def annotate(keys):
            result = []
            for key in keys:
                doc, section = indexed[key]
                result.append({
                    "doc_id": doc["doc_id"], "section_id": section["section_id"],
                    "text": section["text"],
                    "metadata": {k: v for k, v in doc.items() if k != "sections"},
                })
            return result

        copies = {}
        for key, (doc, section) in indexed.items():
            if not doc.get("copied_from"):
                continue
            source = [other_key for other_key, (other_doc, other_section) in indexed.items()
                      if other_doc["doc_id"] == doc["copied_from"]
                      and other_section["text"] == section["text"]]
            assert len(source) == 1, "Do not guess ambiguous copy origins"
            copies[key] = source[0]
        mode = item.get("mode", "scored")
        record = {
            "case_id": case["id"], "category": case["id"][0],
            "dimensions": item["dimensions"], "mode": mode,
            "original_query": case["messages"][0]["content"],
            "corpus": relative(corpus), "corpus_sha256": digest(corpus),
            "necessary_evidence": annotate(item["evidence"]),
            "context_evidence": annotate(item.get("context_evidence", [])),
            "no_answer": item.get("no_answer", False),
            "requires_both_conflict_sides": item.get("conflict", False),
            "requires_cross_document_evidence": item.get("cross_document", False),
            "may_require_followup_search_if_incomplete": item.get("cross_document", False),
            "entry_evidence_any_of": item.get("entry_evidence", []),
            "copy_to_original": copies,
            "annotation_basis": item["basis"],
            "annotation_uncertainty": item.get("uncertainty"),
            "design_setup_not_passed_to_search": case["setup"],
            "business_answer_kind": "exploratory" if mode == "exploratory" else (
                "no_answer" if item.get("no_answer") else (
                    "conflict_report" if item.get("conflict") else (
                        "scope_options" if case["id"] == "C04" else "determinate"))),
        }
        records.append(record)
    positive = [c for c in records if c["necessary_evidence"] and c["mode"] == "scored"]
    assert len(positive) == 25
    assert sum(len(c["necessary_evidence"]) for c in positive) == 37
    assert sum(c["requires_both_conflict_sides"] for c in records) == 9
    assert sum(c["business_answer_kind"] == "determinate" for c in records) == 15
    gold = {key: value for key, value in specification.items() if key != "selected_cases"}
    gold["cases"] = records
    gold["frozen_at_utc"] = datetime.now(timezone.utc).isoformat()
    gold["cases_sha256"] = digest(design_root / "cases.json")
    write_json(folder / "gold.json", gold)
    receipt = {
        "stage": "gold_frozen_before_search",
        "frozen_at_utc": gold["frozen_at_utc"],
        "gold_sha256": digest(folder / "gold.json"),
        "annotation_spec_sha256": digest(args.spec),
        "runner_sha256": digest(__file__),
        "source_sha256": digest(SOURCE),
        "zip_sha256": digest(args.archive),
        "zip_filename": args.archive.name,
        "initial_observation": "Initial read-only git status showed a clean worktree; no tracked changes existed.",
        "git_at_freeze": snapshot(),
        "input_sha256": {relative(p): digest(p) for p in sorted(design_root.rglob("*")) if p.is_file()},
    }
    write_json(folder / "freeze_receipt.json", receipt)
    print(json.dumps({"gold_sha256": receipt["gold_sha256"], "selected": len(records),
                      "excluded": gold["excluded_case_ids"], "search_executed": False}, ensure_ascii=False))


def measure(gold, candidates):
    """Strict original-section metrics; copies have a separate bounded score."""
    returned = {evidence_key(hit) for hit in candidates}
    required = {evidence_key(item) for item in gold["necessary_evidence"]}
    canonical = {gold["copy_to_original"].get(key, key) for key in returned}
    matched = required & returned
    canonical_matched = required & canonical
    context = {evidence_key(item) for item in gold["context_evidence"]}
    meaningful = bool(required) and gold["mode"] == "scored"
    return {
        "necessary_count": len(required), "matched": sorted(matched),
        "missing": sorted(required - returned),
        "recall": len(matched) / len(required) if meaningful else None,
        "hit": bool(matched) if meaningful else None,
        "all_necessary_recalled": required <= returned if meaningful else None,
        "conflict_complete": required <= returned if gold["requires_both_conflict_sides"] else None,
        "canonical_recall": len(canonical_matched) / len(required) if meaningful else None,
        "canonical_conflict_complete": required <= canonical if gold["requires_both_conflict_sides"] else None,
        "crossdoc_entry_hit": bool(returned & set(gold["entry_evidence_any_of"]))
        if gold["requires_cross_document_evidence"] else None,
        "crossdoc_all_evidence": required <= returned if gold["requires_cross_document_evidence"] else None,
        "no_answer_any_candidate": bool(candidates) if gold["no_answer"] is True else None,
        "no_answer_unrelated_candidates": sorted(returned - context)
        if gold["no_answer"] is True else None,
        "no_answer_context_candidates": sorted(returned & context)
        if gold["no_answer"] is True else None,
        "returned_count": len(candidates),
        "copy_candidate_count": sum(evidence_key(hit) in gold["copy_to_original"] for hit in candidates),
        "strict_pass": None if gold["mode"] != "scored" else (
            not bool(returned - context) if gold["no_answer"] else required <= returned
        ),
    }


def aggregate(rows):
    positives = [r for r in rows if r["metrics"]["recall"] is not None]
    conflict = [r for r in rows if r["metrics"]["conflict_complete"] is not None]
    negative = [r for r in rows if r["metrics"]["no_answer_any_candidate"] is not None]
    crossdoc = [r for r in rows if r["metrics"]["crossdoc_entry_hit"] is not None]
    determinate = [r for r in positives if r["business_answer_kind"] == "determinate"]
    scored = [r for r in rows if r["metrics"]["strict_pass"] is not None]
    necessary = sum(r["metrics"]["necessary_count"] for r in positives)
    return {
        "positive_n": len(positives), "necessary_n": necessary,
        "recall_macro": statistics.mean(r["metrics"]["recall"] for r in positives) if positives else None,
        "recall_micro": sum(len(r["metrics"]["matched"]) for r in positives) / necessary if necessary else None,
        "hit": [sum(r["metrics"]["hit"] for r in positives), len(positives)],
        "determinate_hit": [sum(r["metrics"]["hit"] for r in determinate), len(determinate)],
        "conflict_complete": [sum(r["metrics"]["conflict_complete"] for r in conflict), len(conflict)],
        "canonical_conflict_complete": [sum(r["metrics"]["canonical_conflict_complete"] for r in conflict), len(conflict)],
        "negative_any_candidate": [sum(r["metrics"]["no_answer_any_candidate"] for r in negative), len(negative)],
        "negative_any_unrelated": [sum(bool(r["metrics"]["no_answer_unrelated_candidates"]) for r in negative), len(negative)],
        "crossdoc_entry": [sum(r["metrics"]["crossdoc_entry_hit"] for r in crossdoc), len(crossdoc)],
        "crossdoc_complete": [sum(r["metrics"]["crossdoc_all_evidence"] for r in crossdoc), len(crossdoc)],
        "strict_pass": [sum(r["metrics"]["strict_pass"] for r in scored), len(scored)],
    }


def explain(KnowledgeBase, corpus, query):
    """Reconstruct the documented lexical formula for diagnosis, not new search."""
    terms = KnowledgeBase._terms(KnowledgeBase.expand_query(query))
    minimum = 1 if len(terms) <= 2 else 2
    diagnostics = []
    for doc in read_json(corpus):
        for section in doc.get("sections", []):
            text = " ".join([doc.get("title", ""), section.get("text", ""), " ".join(doc.get("tags", []))])
            overlap = terms & KnowledgeBase._terms(text)
            diagnostics.append({
                "doc_id": doc["doc_id"], "section_id": section["section_id"],
                "query_terms": sorted(terms), "matching_terms": sorted(overlap),
                "minimum_overlap": minimum, "passes_overlap_gate": len(overlap) >= minimum,
                "unrounded_score": len(overlap) / max(1, len(terms)),
                "scope_not_indexed": doc.get("scope"),
            })
    eligible = sorted([d for d in diagnostics if d["passes_overlap_gate"]],
                      key=lambda d: (-d["unrounded_score"], d["doc_id"], d["section_id"]))
    ranks = {evidence_key(d): i for i, d in enumerate(eligible, 1)}
    for d in diagnostics:
        d["reconstructed_rank_not_additional_search"] = ranks.get(evidence_key(d))
    return diagnostics


def summarize(rows, gold, manifest):
    output = ["# 修改前原始查询检索基线", "", f"运行：`{manifest['run_id']}`；commit `{manifest['git_at_run']['commit_sha']}`。",
              "", "仅直接调用当前 KnowledgeBase.search；未调用模型或完整 Agent。结论不能外推为完整 Agent 失败。",
              "", "## 指标定义与分母", "",
              "- 执行27个设计用例×4个k=108次search；R05为探索性，排除4行；33个设计用例未执行。",
              "- 主 Recall@k：每题原始doc_id+section_id的必要证据命中数/必要数，宏平均为主，另列微平均。正例25题（37个必要条款），排除R05、无答案R06；冲突题可据资料报告冲突，亦属于有必要证据题。",
              "- Hit@k：上述25题中至少命中一个必要条款的题数；另报确定答案子集15题，排除9个冲突题和范围未明确的C04。Hit不能代替完整证据覆盖。",
              "- 冲突完整召回：9题所有必要冲突条款均进入候选。C12为同一文档的两个section。",
              "- 跨文档：R09、C11共2题，分别报告入口（任一标注入口）和全部必要依据；不模拟后续工具调用。",
              "- 无答案：仅R06一题，分报任何候选、真正无关候选和相关边界说明。不能将evidence_ids为空一概当负例；否定回答的R08有明确正例证据。",
              "- 分类通过：正例必要证据全部命中；无答案无真正无关候选。它是检索覆盖准则，不是业务答题通过率；R06有候选不等于有申请办法。",
              "- 主指标严格要求原始证据；补充指标按copied_from折叠，每条原始证据最多计一次，副本不增加分母或权威。",
              "", "## 总体结果", "",
              "|k|Recall宏|Recall微|Hit/25|确定答案Hit/15|冲突完整/9|折叠副本冲突完整/9|跨文档入口/2|跨文档完整/2|分类通过/26|",
              "|---|---|---|---|---|---|---|---|---|---|"]
    metrics = {}
    fraction = lambda pair: f"{pair[0]}/{pair[1]}"
    for k in KS:
        values = aggregate([r for r in rows if r["k"] == k])
        metrics[str(k)] = values
        output.append(f"|{k}|{values['recall_macro']:.2%}|{values['recall_micro']:.2%}|" +
                      "|".join(fraction(values[key]) for key in ["hit", "determinate_hit", "conflict_complete", "canonical_conflict_complete", "crossdoc_entry", "crossdoc_complete", "strict_pass"]) + "|")
    output += ["", "## 按设计类别的完整证据通过数/总数", "", "|类别|k=1|k=3|k=5|k=10|", "|---|---|---|---|---|"]
    for category in ["R", "C", "X"]:
        output.append("|" + category + "|" + "|".join(fraction(aggregate([r for r in rows if r['k'] == k and r['category'] == category])["strict_pass"]) for k in KS) + "|")
    output += ["", "## 各具体维度", "", "|维度|k=1|k=3|k=5|k=10|", "|---|---|---|---|---|"]
    dimensions = sorted({d for c in gold["cases"] if c["mode"] == "scored" for d in c["dimensions"]})
    for dim in dimensions:
        output.append("|" + dim + "|" + "|".join(fraction(aggregate([r for r in rows if r['k'] == k and dim in r['dimensions']])["strict_pass"]) for k in KS) + "|")
    output += ["", "## 全部用例证据覆盖", "", "|case|k=1命中/必要|k=3|k=5|k=10|", "|---|---|---|---|---|"]
    for case in gold["cases"]:
        cells = []
        for k in KS:
            row = next(r for r in rows if r["case_id"] == case["case_id"] and r["k"] == k)
            metric = row["metrics"]
            cells.append(f"{len(metric['matched'])}/{metric['necessary_count']}" if metric["recall"] is not None else "探索性" if case["mode"] == "exploratory" else f"候选{metric['returned_count']}，无关{len(metric['no_answer_unrelated_candidates'])}")
        output.append("|" + case["case_id"] + "|" + "|".join(cells) + "|")
    output += ["", "## 原始缺失与实际候选", ""]
    for row in rows:
        if row["metrics"]["recall"] is not None and not row["metrics"]["all_necessary_recalled"]:
            candidates = ", ".join(f"{c['rank']}:{evidence_key(c)}({c['score']})" for c in row["candidates"]) or "空"
            output.append(f"- {row['case_id']} k={row['k']}：缺失 {row['metrics']['missing']}；实际候选 {candidates}。诊断：{'; '.join(row['failure_reasons'])}。")
    output += ["", "## 复现", "", "```powershell", manifest["reproduction_command"], "```", "",
               "该命令使用已冻结gold并向新replay01目录写结果；目录存在时请指定新的输出目录，程序不会覆盖既有结果。",
               "", "## 限制", "",
               "单次首次原始查询；只计search函数调用耗时，另存加载耗时；未预热、样本短且噪声重复，耗时不作性能基准。",
               "R04的RD含义来自设计setup，未追加到查询。R05意图不确定，单独报告。R06只有一条负例且具有边界说明，不能推断一般负例误召回率。",
               "候选分数保留生产函数的三位小数；程序实际排序使用未舍入分数。诊断分数/全库位置依据源代码公式重建并明确标记，不是额外检索结果。",
               "用例关联，R01=C02等存在重复，宏平均不代表独立抽样或统计显著性。尚未检验改写、追问、模型冲突裁决、工具失败、预算或注入防御。"]
    return "\n".join(output) + "\n", metrics


def run(args):
    folder = args.run_dir.resolve()
    receipt = read_json(folder / "freeze_receipt.json")
    assert args.gold_sha256 == receipt["gold_sha256"] == digest(folder / "gold.json"), "Gold changed"
    assert receipt["source_sha256"] == digest(SOURCE), "Baseline search source changed"
    assert receipt["runner_sha256"] == digest(__file__), "Runner changed since freeze"
    for path, expected in receipt["input_sha256"].items():
        assert digest(ROOT / path) == expected, f"Input changed: {path}"
    gold = read_json(folder / "gold.json")
    output = args.output.resolve() if args.output else folder
    output.mkdir(parents=True, exist_ok=True)
    assert not any((output / name).exists() for name in ["results.jsonl", "manifest.json", "summary.md", "metrics.json"]), "Refuse to overwrite results"
    if output != folder:
        for name in ["gold.json", "freeze_receipt.json"]:
            with (output / name).open("xb") as stream:
                stream.write((folder / name).read_bytes())
    # Import the actual file; avoid importing any Agent/model/framework package.
    spec = importlib.util.spec_from_file_location("baseline_knowledge", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    KnowledgeBase = module.KnowledgeBase
    started = datetime.now(timezone.utc).isoformat()
    before = snapshot()
    rows = []
    for case in gold["cases"]:
        corpus = ROOT / case["corpus"]
        assert digest(corpus) == case["corpus_sha256"]
        indexed = sections(read_json(corpus))
        diagnostic = explain(KnowledgeBase, corpus, case["original_query"])
        indexed_diagnostic = {evidence_key(d): d for d in diagnostic}
        for k in KS:
            load_start = perf_counter_ns()
            kb = KnowledgeBase(corpus)
            load_ms = (perf_counter_ns() - load_start) / 1e6
            start = perf_counter_ns()
            error = None
            try:
                actual = kb.search(case["original_query"], limit=k)
            except Exception as exc:
                actual = []
                error = f"{type(exc).__name__}: {exc}"
            elapsed_ms = (perf_counter_ns() - start) / 1e6
            candidates = []
            for rank, hit in enumerate(actual, 1):
                doc, _ = indexed[evidence_key(hit)]
                candidates.append({**hit, "rank": rank,
                                   "corpus_metadata": {key: val for key, val in doc.items() if key != "sections"}})
            reconstructed = sorted([d for d in diagnostic if d["passes_overlap_gate"]],
                                   key=lambda d: d["reconstructed_rank_not_additional_search"])[:k]
            if error is None:
                assert [evidence_key(hit) for hit in actual] == [evidence_key(d) for d in reconstructed], "Diagnostics do not match actual ranking"
            measurement = measure(case, candidates)
            if error:
                measurement["strict_pass"] = False if case["mode"] == "scored" else None
            failures = []
            for key in measurement["missing"]:
                d = indexed_diagnostic[key]
                if not d["passes_overlap_gate"]:
                    failures.append(f"{key}词项重合{len(d['matching_terms'])}小于门槛{d['minimum_overlap']}")
                else:
                    failures.append(f"{key}按源公式重建位置{d['reconstructed_rank_not_additional_search']}超出Top-{k}")
            if error:
                failures.append(error)
            rows.append({
                "case_id": case["case_id"], "category": case["category"],
                "dimensions": case["dimensions"], "business_answer_kind": case["business_answer_kind"],
                "query": case["original_query"], "corpus": case["corpus"],
                "corpus_sha256": case["corpus_sha256"], "k": k,
                "candidates": candidates, "metrics": measurement,
                "search_elapsed_ms": elapsed_ms, "load_elapsed_ms": load_ms,
                "error": error, "failure_reasons": failures,
                "annotation_uncertainty": case["annotation_uncertainty"],
                "lexical_diagnostics_reconstructed_from_source": diagnostic,
            })
    after = snapshot()
    assert before["tracked_file_sha256"] == after["tracked_file_sha256"], "Tracked files changed during evaluation"
    assert digest(folder / "gold.json") == receipt["gold_sha256"]
    for path, expected in receipt["input_sha256"].items():
        assert digest(ROOT / path) == expected, f"Input changed during evaluation: {path}"
    # Freeze compared extracted bytes against the user archive; these hashes pin them.
    design_root = folder / "input/qa_boundary_test_design"
    by_id = {c["id"]: c for c in read_json(design_root / "cases.json")["cases"]}
    manifest = {
        "run_id": output.name, "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "app_version": read_json_version(), "git_at_run": before,
        "tracked_files_unchanged_after_run": True,
        "git_at_annotation_freeze": receipt["git_at_freeze"],
        "initial_workspace_observation": receipt["initial_observation"],
        "agents_md": "No AGENTS.md found in repository or checked ancestor paths",
        "gold_sha256": receipt["gold_sha256"], "frozen_at_utc": gold["frozen_at_utc"],
        "runner_sha256": digest(__file__), "knowledge_source_sha256": digest(SOURCE),
        "zip_filename": receipt["zip_filename"], "zip_sha256": receipt["zip_sha256"],
        "input_sha256": receipt["input_sha256"],
        "config": {"k": list(KS), "query_mode": "original_messages[0].content", "corpus_reload_per_case_and_k": True,
                   "search_defaults_changed": False, "production_aliases": module.QUERY_ALIASES,
                   "external_rewriting": False, "model_calls": 0, "agent_runs": 0,
                   "search_calls": len(rows), "timing": "single perf_counter_ns measurement; KB loading separate",
                   "index_fields": ["title", "section.text", "tags"],
                   "not_indexed_metadata": ["scope", "doc_id", "version", "effective_from"],
                   "ranking": "unrounded_overlap_fraction desc, doc_id asc, section_id asc",
                   "overlap_gate": "1 when query term count <=2; otherwise 2", "k_clamp": [1, 10]},
        "counts": {"design_cases": len(by_id), "executed_cases": len(gold["cases"]),
                   "scored_cases": sum(c["mode"] == "scored" for c in gold["cases"]),
                   "excluded_but_executed": gold["excluded_case_ids"],
                   "not_executed": gold["not_executed_case_ids"], "results": len(rows),
                   "execution_errors": sum(r["error"] is not None for r in rows)},
        "not_executed_reason": gold["not_executed_reason"],
        "reproduction_command": f'.\\.venv\\Scripts\\python.exe -B scripts/retrieval_baseline.py run --run-dir {relative(folder)} --gold-sha256 {receipt["gold_sha256"]} --output {relative(folder)}/replay01',
    }
    with (output / "results.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary, metrics = summarize(rows, gold, manifest)
    write_json(output / "manifest.json", manifest)
    write_json(output / "metrics.json", metrics)
    with (output / "summary.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(summary)
    print(json.dumps({"counts": manifest["counts"], "metrics": metrics}, ensure_ascii=False, indent=2))


def read_json_version():
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--run-dir", type=Path, required=True)
    freeze_parser.add_argument("--spec", type=Path, required=True)
    freeze_parser.add_argument("--archive", type=Path, required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--run-dir", type=Path, required=True)
    run_parser.add_argument("--gold-sha256", required=True)
    run_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    (freeze if args.stage == "freeze" else run)(args)


if __name__ == "__main__":
    main()
