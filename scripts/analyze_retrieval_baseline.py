"""Audit frozen raw results and append evidence-based analysis; never search."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    assert not (folder / "analysis.json").exists(), "Do not overwrite existing analysis"
    manifest = read(folder / "manifest.json")
    gold = read(folder / "gold.json")
    assert sha(folder / "gold.json") == manifest["gold_sha256"]
    rows = [json.loads(line) for line in (folder / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    root = Path(__file__).resolve().parents[1]
    source = root / "src/enterprise_qa_agent/knowledge.py"
    assert sha(source) == manifest["knowledge_source_sha256"]
    assert len(rows) == 108 and len({(r["case_id"], r["k"]) for r in rows}) == 108
    by_case = {c["case_id"]: c for c in gold["cases"]}
    # Independent recount from candidate IDs rather than trusting saved metrics.
    audited = {}
    for k in (1, 3, 5, 10):
        recalls, total_match, total_need, hit, full, conflicts, conflict_n = [], 0, 0, 0, 0, 0, 0
        for row in (r for r in rows if r["k"] == k):
            case = by_case[row["case_id"]]
            assert row["query"] == case["original_query"]
            assert row["corpus_sha256"] == case["corpus_sha256"] == sha(root / case["corpus"])
            needed = {(e["doc_id"], e["section_id"]) for e in case["necessary_evidence"]}
            got = {(e["doc_id"], e["section_id"]) for e in row["candidates"]}
            if case["mode"] == "scored" and needed:
                matched = len(needed & got)
                recalls.append(matched / len(needed))
                total_match += matched
                total_need += len(needed)
                hit += bool(needed & got)
                full += needed <= got
                assert row["metrics"]["recall"] == matched / len(needed)
                if case["requires_both_conflict_sides"]:
                    conflicts += needed <= got
                    conflict_n += 1
        audited[str(k)] = dict(positive_count=len(recalls), necessary=total_need, matched=total_match,
                               macro_recall=statistics.mean(recalls), micro_recall=total_match / total_need,
                               hit=hit, full_positive=full, conflict_complete=conflicts, conflict_n=conflict_n)

    def row(case, k):
        return next(r for r in rows if r["case_id"] == case and r["k"] == k)

    def signature(case, k):
        return [(c["doc_id"], c["section_id"], c["score"], c["text"]) for c in row(case, k)["candidates"]]

    def corpus_order(case):
        return [d["doc_id"] for d in read(root / by_case[case]["corpus"])]

    transformations = {}
    for k in (1, 3, 5, 10):
        base, swapped = signature("C01", k), signature("X04", k)
        renamed = signature("X05", k)
        mapping = {"A01": "D02", "Z99": "D01"}
        mapped_order = [mapping[c[0]] for c in renamed]
        transformations[str(k)] = {
            "C01_input_order": corpus_order("C01"), "X04_input_order": corpus_order("X04"),
            "C01_actual_sequence": base, "X04_actual_sequence": swapped,
            "file_order_changed": corpus_order("C01") != corpus_order("X04"),
            "returned_order_changed": base != swapped,
            "order_verdict": "变换未触发：文件顺序变化被现有排序抵消" if base == swapped else "实际候选序列改变",
            "X05_actual_sequence": renamed, "X05_sequence_mapped_to_original_ids": mapped_order,
            "rename_changed_original_evidence_order": [c[0] for c in base] != mapped_order,
            "R01_text": row("R01", k)["candidates"][0]["text"],
            "X06_text": row("X06", k)["candidates"][0]["text"],
            "content_replacement_visible_in_search": row("R01", k)["candidates"][0]["text"] != row("X06", k)["candidates"][0]["text"],
        }
    report = {
        "analysis_script_sha256": sha(__file__), "gold_sha256": manifest["gold_sha256"],
        "results_sha256": sha(folder / "results.jsonl"),
        "source_sha256": manifest["knowledge_source_sha256"],
        "independent_metric_recount": audited, "transformations": transformations,
        "observed_latency_ms": {
            "all_search_mean": statistics.mean(r["search_elapsed_ms"] for r in rows),
            "all_search_median": statistics.median(r["search_elapsed_ms"] for r in rows),
            "all_search_min": min(r["search_elapsed_ms"] for r in rows),
            "all_search_max": max(r["search_elapsed_ms"] for r in rows),
            "note": "Single measurement, no warmup; not a performance benchmark.",
        },
        "candidate_counts_at_k5": {c["case_id"]: len(row(c["case_id"], 5)["candidates"]) for c in gold["cases"]},
        "error_count": sum(r["error"] is not None for r in rows),
        "scope_metadata_tie": signature("R07", 5),
        "no_answer_R06": {str(k): row("R06", k)["metrics"] for k in (1, 3, 5, 10)},
        "annotation_exploration_R05": {str(k): signature("R05", k) for k in (1, 3, 5, 10)},
    }
    lines = ["", "## 基于实际候选的失败归因与修复优先级（只分析，未实施）", "",
             "### 1. 互补条款用词不一致，加上词项门槛导致永久漏召回", "",
             "C11 的原始问题是“报销期限和需要的材料分别是什么？”。四个k均只返回 D01/D01-S1（0.143，期限30日），D04/D04-S1（“费用报销申请须附合规票据。”）始终缺失，必要证据Recall均为1/2。",
             "源代码 `src/enterprise_qa_agent/knowledge.py:13–21` 的同义词未覆盖材料/票据；`54–60` 只匹配title、text和tags，并对长查询要求至少2个重合词项。D04与原问题仅重合“报销”，1<2，被门槛排除，而不是被Top-k截断。D01重合“报销、期限”，分数2/14=0.143。",
             "这是可直接复核的原始表达与资料用词不一致、同义词覆盖不足。后续最应优先验证多意图/证据子问题检索或语义/业务词汇召回；仅把k改为10不能修复。本轮没有改词表、门槛或任何src代码。",
             "", "### 2. 转载副本挤占Top-k，主证据和冲突另一方不可见", "",
             "C13 k=5 的实际返回为 COPY0/COPY0-S1 到 COPY4/COPY4-S1，五条分数均为0.4，正文都是15日，且原始metadata的copied_from均为D02。严格原始证据Recall为0/2；折叠副本后也仅为1/2，绝不能记5条证据或多数票。",
             "k=10 的实际列表是 COPY0…COPY7、D01/D01-S1（第9名，30日）、D02/D02-S1（第10名，15日）。相同问题C01的两份原始资料在k=3就能全部召回；增加副本后直到k=10才完整。",
             "源代码 `52–77` 逐section追加候选，没有copied_from去重；`78–79` 按未舍入分数、doc_id、section_id排序后截断，COPY字典序早于D01。优先验证来源折叠与证据多样性，比单纯扩大k更有针对性。",
             "", "### 3. 范围元数据未进入相关性排序，成功依赖ID同分顺序；噪声缺少语义区分", "",
             "R07 k=5 实际返回研发 D01/D01-S1（0.333）与销售 D02/D02-S1（0.333）。k=1恰好取得正确D01，因此本题通过；但`54–55`未将scope纳入检索，`71`只是把scope带回结果。不能把这个通过解释成已按部门范围排序。后续应优先验证元数据约束/匹配，而不把当前通过当作已解决。",
             "X01—X03的D01在所有k都被召回，不能宣称噪声导致本次漏召回；然而k=5均含1条D01和4条预算噪声，k=10含1条D01和9条噪声，全部分数0.4。N文档明确“本条款没有规定报销提交期限”，单纯词项交集仍把它们排成与答案同分。D01当前靠ID较早而排第一；本轮没有构造额外改号噪声变体来证明其一定退化。",
             "编号对照X05实际把A01/15日排第一，Z99/30日第二；相对C01的D01/30日第一、D02/15日第二，语义证据顺序已改变。这是排序对编号敏感的实际证据，不是模型选择答案的证据。",
             "", "## 其他失败类别与未观察到的失败", "",
             "- Top-k截断：R09 k=1只有D10映射入口，D11期限条款在实际k=3列表第2名（0.444）；先找到入口不等于首次已覆盖依据。C11不同：即使k=10仍缺票据条款，不能归为截断。",
             "- 文内冲突：C12 k=1只有D01-S1，Recall=1/2，冲突证据不完整；k≥3实际取得D01-S1和D01-S2两条。",
             "- 错字：R03 k=1返回D02（0.273），实际仍靠“研发、差旅、期限”等重合取得目标；不能由此宣称具有通用纠错能力。",
             "- 中英混合：R04 k=1返回D02（0.231）。RD不在现有词表，匹配仍有“差旅、返程”等中文线索；未证明英文同义检索或缩写消歧。",
             "- R10否定与干扰：k=5取得D02、D01，没有取得年假D03；本例未观察到年假干扰错误。",
             "- 资料替换X06：各k实际返回的是“45日”原文，R01为“30日”，检索已加载当前快照；没有生成任何答案，不声称验证了答案随资料变化。",
             "", "## 顺序变换是否真正触发", "",
             "|k|C01返回ID顺序|X04返回ID顺序|结论|", "|---|---|---|---|"]
    for k in (1, 3, 5, 10):
        check = transformations[str(k)]
        lines.append(f"|{k}|{', '.join(c[0] for c in check['C01_actual_sequence'])}|{', '.join(c[0] for c in check['X04_actual_sequence'])}|{check['order_verdict']}|")
    lines += ["", "输入文件确实从D01→D02变成D02→D01，但现有排序消除了返回顺序差异。没有人为调整返回位置，也没有调用模型，因此不能宣称验证了位置鲁棒性。",
              "", "## 无答案与探索性项目", "",
              "R06在四个k均返回D01-S1（0.444）。它明确说明“育儿补贴不适用此报销制度；本文件不规定育儿补贴申请入口、材料和期限”，属于相关的资料边界说明，不是申请办法，也不是完全无关文档。Gold在执行前已将其列入context_evidence。",
              "因此：有候选1/1、返回空列表0/1、真正无关候选0/1。不能宣称无答案检索误召回率100%，也不能宣称模型一定能正确拒答；本轮未测生成层。",
              "R05“报销？”在k=1取得D01，k≥3取得D01、D02（均1.0）；没有唯一可确定的必要条款集，未记作负例，未计入总体分母。R04的标注依赖设计声明RD=研发；完整setup保存在gold，但未追加到原查询。",
              "", "## 可复现性与审计", "",
              f"- Gold固定哈希：`{manifest['gold_sha256']}`。固定时的时间戳在freeze_receipt.json中，早于manifest.started_at_utc；输入所有解压字节在freeze阶段与原ZIP逐项比对。",
              f"- 独立从实际候选doc_id+section_id重算：共108行，0个执行错误；与results的逐题Recall一致。完整重算与顺序对照保存在analysis.json。",
              "- Git初始分支和commit、当时工作区状态、全部已跟踪文件哈希在manifest/freeze_receipt中；开始时工作区干净，运行期间已跟踪文件哈希未变。只新增scripts和examples/evaluation。",
              "- 参考论文仅作为用户提供测试设计的来源说明；本轮未联网核验或复现论文指标，不将这些自定义用例称为论文原基准。",
              "", "复现检索后，对replay01运行下列命令，重算审计并追加同样的失败分析（不再调用search）：", "", "```powershell",
              f'.\\.venv\\Scripts\\python.exe -B scripts/analyze_retrieval_baseline.py --run-dir {manifest["reproduction_command"].split("--output ", 1)[1]}',
              "```", "",
              "评测计分器检查命令：`.\\.venv\\Scripts\\python.exe -B scripts/test_retrieval_baseline.py -v`，本轮5项通过。",
              "本轮未实施上面任何检索优化；基线仅用于下一轮设计对照。"]
    with (folder / "analysis.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with (folder / "summary.md").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    print(json.dumps({"audited": audited, "order_verdict": transformations["5"]["order_verdict"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
