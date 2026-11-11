"""Verify final experiment artifacts and create an immutable receipt, no model calls."""
import json
import re
from collections import Counter
from pathlib import Path
from coverage_experiment import OUT
import agent_baseline as base

rows=[json.loads(s) for s in (OUT/"results.jsonl").read_text(encoding="utf-8").splitlines()]
assert Counter(r["config"] for r in rows)=={"B":18,"dedup_rewrite":18,"pilot_C11":3,"dev_B":3,"dev_combo":3}
assert len({(r["config"],r["run_id"]) for r in rows})==45
before=base.read(OUT/"before.json")
assert all(base.sha(base.ROOT/p)==h for p,h in before["historical_hashes"].items())
manifests={}
errata=[]
for folder in ["B","dedup_rewrite","pilot_C11","B_launcher_recovery","dev_B","dev_combo"]:
    manifests[folder]=base.check(OUT/folder)
    plan=base.read(OUT/folder/"plan.json")
    cases={c["case_id"]:c for c in plan["cases"]}
    actual_turns=sum(len(cases[r["case_id"]]["messages"]) for r in plan["runs"])
    if manifests[folder]["user_turn_count"]!=actual_turns:
        errata.append(dict(folder=folder,field="user_turn_count",frozen_value=manifests[folder]["user_turn_count"],
            actual_planned_turns=actual_turns,reason="子集计划生成器统计了唯一case的轮数，未乘重复次数；保留原清单，补充本勘误。不涉及模型/预算/语料。"))

for row in rows:
    trace=base.read(base.ROOT/row["trace"])
    expected_mode="dedup" if row["config"] in {"dedup_rewrite","dev_combo"} else "original"
    assert trace["experiment_config"]["retrieval_mode"]==expected_mode
    assert trace["experiment_config"]["demand_rewrite"] is True
    assert base.sha(base.ROOT/row["corpus"])==row["corpus_sha256"]
    assert base.read(OUT/"per_run"/row["config"]/(row["run_id"]+".json"))==row
    counts=Counter(s["turn"] for s in row["steps"] if s["type"]=="tool_call")
    assert max(counts.values())<=4
    assert sum(counts.values())==row["tool_calls"]
    for event in row["coverage_reports"]:
        assert event["source"]=="model_tool_argument" and event["validated_semantically"] is False
    metadata=base.read((base.ROOT/row["trace"]).parent.parent/"reply_metadata.json")
    assert all(m["finished_reason"]=="completed" and m["error"] is None for m in metadata)
    # Independent recomputation of successful underlying query counts.
    stats=[s["complete_return"]["retrieval_statistics"] for s in row["steps"] if "retrieval_statistics" in s["complete_return"]]
    assert sum(v["underlying_queries_this_call"] for v in stats)==row["underlying_queries"]
base.write(OUT/"manifest_errata.json",errata)

lines=["# 逐场景对照与补充核验", "", "旧结果只读取；本表不改变判定或gold。完整记录路径见Trace列，工具完整返回保存在相邻sessions目录。", "",
    "|配置|场景|次数|首次完整|累计完整|业务通过|completed且通过|",
    "|---|---|---|---|---|---|---|"]
for config in ["B","dedup_rewrite"]:
    for case in base.IDS:
        group=[r for r in rows if r["config"]==config and r["case_id"]==case]
        denom=len(group)
        evidence=all(r["required"] for r in group)
        first=f"{sum(r['first_recall']==1 for r in group)}/{denom}" if evidence else "不适用"
        complete=f"{sum(not r['missing'] for r in group)}/{denom}" if evidence else "不适用"
        lines.append(f"|{config}|{case}|{denom}|{first}|{complete}|{sum(r['review']['strict_business_pass'] for r in group)}/{denom}|{sum(r['review']['completed_and_business_pass'] for r in group)}/{denom}|")
lines += ["", "## C13实际返回与断言核验", "", "|配置/运行|首次真实候选键|最终必要键缺口|业务|Trace|", "|---|---|---|---|---|"]
for r in rows:
    if r["case_id"]!="C13":continue
    path=Path(r["trace"]).relative_to(Path(base.rel(OUT))).as_posix()
    first=next(s for s in r["steps"] if s["tool"]=="search_docs")
    lines.append(f"|{r['config']}/{r['run_id']}|{', '.join(first['visible_keys'])}|{', '.join(r['missing']) or '无'}|{r['review']['strict_business_pass']}|[记录]({path})|")
lines += ["", "组合r3的‘通用范围’原句、实际scope未提供和严格失败判定见[逐条结果](per_run/dedup_rewrite/C13_r3.json)。其主答案并列冲突并追问正确；未提供范围却被称通用，属于附带断言失败。C12措辞与此不同：同一文档未列范围差异，最终也说明范围缺失，不据此声称通用适用。", "",
    "## 资料不足与多轮路径", "", "|配置/场景|核验结论|实际记录|", "|---|---|---|"]
for r in rows:
    if r["config"] not in {"B","dedup_rewrite"} or r["case_id"] not in {"E03","F01","M01","R07"}:continue
    path=Path(r["trace"]).relative_to(Path(base.rel(OUT))).as_posix()
    lines.append(f"|{r['config']}/{r['case_id']}|{r['review']['reason']}|[Trace]({path})|")
lines += ["", "开发题没有重复条款，同一查询在两种检索模式的结果相同。dev_B与dev_combo的差异来自模型自主路径/查询差异，不能归因于去重本身。DEV01的环节不确定性同时报告并从开发业务总体分母剔除；其两条原始证据的可见性仍可确定。", "",
    "两组C11成功运行均在第二步已获得完整且含scope/版本/日期的原文片段，之后仍各读取两份：B_r2与组合_r3共4次读取，未增加必要条款。与先测r2的第五次拒绝一起说明，结束行为并未被机制可靠保证。", "",
    "冻结清单字段勘误见[manifest_errata.json](manifest_errata.json)：pilot_C11的user_turn_count原写1（唯一用例轮数），实际计划/执行3次单轮。保留清单原字节，不据错误字段少算实际模型运行。", ""]
(OUT/"comparison_details.md").write_text("\n".join(lines),encoding="utf-8")

# Validate all new Markdown links (external links are not used for this report).
checked=0
for doc in OUT.glob("*.md"):
    for target in re.findall(r"\]\(([^)]+)\)",doc.read_text(encoding="utf-8")):
        if "://" not in target and not target.startswith("#"):
            assert (doc.parent/target.split("#")[0]).exists(), (doc,target)
            checked+=1
receipt=dict(verified_at_utc=base.now(),source_commit=base.git("rev-parse","HEAD"),
    real_trials=45,main_trials=36,pilot_trials=3,development_trials=6,user_turns=47,
    pre_model_launch_failures_preserved=4,model_replies_completed=47,
    historical_files_unchanged=len(before["historical_hashes"]),
    protected_manifests_checked=list(manifests),markdown_links_checked=checked,
    tests=base.read(OUT/"tests.json"),
    source_hashes={base.rel(p):base.sha(p) for p in (base.ROOT/"src").rglob("*.py")},
    script_hashes={base.rel(p):base.sha(p) for p in (base.ROOT/"scripts").glob("*demand_rewrite.py")},
    artifacts_sha256={p.relative_to(OUT).as_posix():base.sha(p) for p in OUT.rglob("*") if p.is_file()},
    git_staged_diff=base.git("diff","--cached","--stat"))
assert receipt["git_staged_diff"]==""
base.write(OUT/"final_receipt.json",receipt)
print(json.dumps({k:v for k,v in receipt.items() if k not in {"artifacts_sha256","script_hashes","source_hashes","tests"}},ensure_ascii=False,indent=2))
