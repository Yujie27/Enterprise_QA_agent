"""Build A＋去重 comparison using frozen retrieval gold and reviewed real traces."""
import json
from pathlib import Path
from agent_baseline import ROOT, BASELINE, read, write, sha, rel
from dedup_experiment import EXPERIMENT

agent = EXPERIMENT / "agent"
rows = [json.loads(line) for line in (agent / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
reviews = {r["run_id"]: r for r in read(agent / "reviews.json")["reviews"]}
old_agent = ROOT / "examples/evaluation/agent_baseline/20261110_original_agent_v020"
old = {r["run_id"]: r for line in (old_agent / "results.jsonl").read_text(encoding="utf-8").splitlines() if (r := json.loads(line))}
assert len(rows) == len(reviews) == 18
assert read(agent / "manifest.json")["model_config"] == read(old_agent / "manifest.json")["model_config"]
for row in rows:
    row["review"] = reviews[row["run_id"]]
    row["before_business_pass"] = old[row["run_id"]]["manual_review"]["strict_pass"]
    row["execution_and_business_pass"] = row["review"]["business_pass"] and row["execution_status"] not in {"incomplete", "failed", "no_trace"}
    if row["review"].get("unsupported_quote"):
        assert row["review"]["unsupported_quote"] in row["final_answer"]
    if row["case_id"] == "C13":
        assert row["all_visible_complete"]
        observed_sources = [s for step in row["tool_steps"] for hit in step["full_tool_return"].get("results", [])
                            for s in hit.get("source_info", {}).get("sources", [])]
        assert sum(s["relationship"] == "verified_copy" for s in observed_sources) >= 8
with (agent / "results.jsonl").open("x", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
before_metrics = read(BASELINE / "metrics.json")
after_metrics = read(EXPERIMENT / "retrieval_metrics.json")
retrieval = [json.loads(line) for line in (EXPERIMENT / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()]
doc = ["# A＋去重 独立实验", "",
       "仅改变候选整理：原匹配候选→精确证据折叠→原排序→Top-k。提示词、模型、同义词、匹配门槛、分数公式、默认k和每轮4次工具预算均未改。",
       "起始commit与工作区已有差异、业务代码和所有历史结果哈希见before.json；执行前封存，历史文件保持原样。",
       "", "## 实现边界", "",
       "原文、scope、version、effective_from严格相等才属于内容组。copied_from必须指向实际存在、唯一匹配、非转载的原始条款；已通过原匹配门槛的原始候选可作为代表，不以副本数量加分，不绕过门槛取未匹配的原件。没有转载字段的相同内容仅标content_duplicate_only。来源缺失或不一致的声明保留为独立候选，标unverified_copy；不编造来源。",
       "不同数字、时间单位、否定、起算点、范围、例外或版本日期因精确文本/元数据不同而保留；同文档两个冲突section不合并。source_info返回实际成员ID、声明的来源及核验状态，让模型只按可见信息叙述来源。此实现保守，不进行语义近似去重。",
       "", "## 工程验证", "",
       "已有11项及新增6项共17项测试通过，见tests.json。首轮沙箱临时目录权限失败被保留说明，沙箱外同代码17/17通过。新增测试见tests/test_dedup.py。",
       "独立开发变体：zeta/omega、17份archive-*转载，不使用COPY前缀；实际k=3/5/10均取得两个原始规则，k=1只一个。development_variant.json和development_results.json保存原始输入与实际输出，不纳入冻结27用例分母。",
       "", "## 冻结检索对照", "",
       f"Gold未改，SHA256 `{sha(BASELINE / 'gold.json')}`。27用例×4k=108次调用；R05探索性排除，正例25题37条款、冲突9题。保持原始问题，各用例独立加载指定语料。",
       "|k|A Recall宏→A＋去重|A Recall微→A＋去重|冲突完整A→A＋去重|来源折叠冲突完整A→A＋去重|", "|---|---|---|---|---|"]
for k in ["1", "3", "5", "10"]:
    a, b = before_metrics[k], after_metrics[k]
    doc.append(f"|{k}|{a['recall_macro']:.0%}→{b['recall_macro']:.0%}|{a['recall_micro']:.2%}→{b['recall_micro']:.2%}|{a['conflict_complete'][0]}/9→{b['conflict_complete'][0]}/9|{a['canonical_conflict_complete'][0]}/9→{b['canonical_conflict_complete'][0]}/9|")
doc += ["", "来源折叠后的必要证据Recall宏平均（每个原始条款最多计一次）：", "", "|k|A|A＋去重|", "|---|---|---|"]
for k in [1, 3, 5, 10]:
    group = [r for r in retrieval if r["k"] == k and r["metrics"]["recall"] is not None]
    a = sum(r["before_metrics"]["canonical_recall"] for r in group) / len(group)
    b = sum(r["metrics"]["canonical_recall"] for r in group) / len(group)
    doc.append(f"|{k}|{a:.0%}|{b:.0%}|")
doc += ["", "C13：k=5从5份15日副本、严格Recall=0/2（按来源折叠后1/2），变为真实D01/30日与D02/15日两个代表、严格和折叠Recall均2/2。没有把gold改成只需命中一个来源。k=1容量仍不足双方，不能判冲突证据完整。",
        "逐例候选与前后指标在retrieval_results.jsonl；必要证据Recall退化列表：" + str(read(EXPERIMENT / "retrieval_manifest.json")["regressions"]),
        "", "|用例|k|返回候选是否变化（含来源元数据）|严格Recall前→后|折叠来源Recall前→后|", "|---|---|---|---|---|"]
for r in retrieval:
    if r["candidate_changed"]:
        doc.append(f"|{r['case_id']}|{r['k']}|是|{r['before_metrics']['recall']}→{r['metrics']['recall']}|{r['before_metrics']['canonical_recall']}→{r['metrics']['canonical_recall']}|")
doc += ["", "除C13外，X01—X03的重复预算噪声也被内容折叠，候选减少但必要证据未退化。C11原始查询仍只有D01，D04词项门槛问题未被去重修复。其他用例实际候选不变。",
        "", "## 18次真实Agent对照", "",
        "复用原Agent运行器和语料：12个场景，各一次；C01/C11/C13额外两次。模型deepseek-flash，配置与A清单逐字段相等，温度/top_p/seed仍为服务默认；4次每轮工具预算未增。全部18次实际运行，0次未执行，无Mock。",
        "业务通过和执行完成分开：A业务10/18；A＋去重业务" + str(sum(r["review"]["business_pass"] for r in rows)) + "/18；同时执行结束且业务通过" + str(sum(r["execution_and_business_pass"] for r in rows)) + "/18。两次incomplete不伪称正常完成，即使已有答案可由已取得证据支持。",
        "|运行|A业务通过|A＋去重业务通过|执行状态|工具数|证据完整|判定和Trace|", "|---|---|---|---|---|---|---|"]
for row in rows:
    trace = Path(row["trace_path"]).relative_to(EXPERIMENT.relative_to(ROOT)).as_posix()
    doc.append(f"|{row['run_id']}|{row['before_business_pass']}|{row['review']['business_pass']}|{row['execution_status']}|{row['tool_calls']}|{row['all_visible_complete']}|[Trace]({trace})；{row['review']['reason']}|")
doc += ["", "### 核心结论", "",
        "1. **去重解决了本次C13的重复候选挤占**：检索k=5严格与折叠证据覆盖0/2、1/2→2/2；Agent三次均首次取得D01与D02，读取双方后并列冲突、请求确认，没有先按15日执行的建议。来源信息由实际source_info提供，八个副本的描述可以复核。C13最终业务0/3→3/3。",
        "2. **冲突覆盖改善**：冻结9题在k=3/5由8/9→9/9，k=1仍0/9，k=10仍9/9。主指标严格原始doc+section；来源折叠指标另列，没有用副本数量提高分数。",
        "3. **回答改善但非全部可归因去重**：C13的候选变化与取得冲突双方有直接可见链条。C11语料没有重复，原始查询检索仍漏D04，本次三次Agent自主改写碰巧都取得材料，不能归因去重；其中两次额外追查触顶incomplete。C05本次不再先建议15日，同样无检索变化，属于采样波动。",
        "4. **仍有回答约束和工程预算问题**：C01_r2仍建议先按15日，提示词没有修。F01_r1正确识别故障但编造发生时间并标UTC，严格业务不通过，是相对A的新退化；故障返回文本不含该时间。E03未补造工作日/自然日口径，M01继承上下文，单证据R01/C02正常。",
        "后续B可单独验证材料/票据的词汇与多意图召回；C可单独验证独立冲突来源补查；D或回答依据约束应检查无依据执行建议、起算口径、错误时间和过度查证后的预算不足。上述都没有混入“A＋去重”。",
        "", "## 复现", "", "```powershell",
        ".\\.venv\\Scripts\\python.exe -B -m unittest discover -s tests -v",
        "# scripts/dedup_experiment.py retrieval：复用冻结gold，拒绝覆盖已有结果；新实验需另指定输出目录",
        ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py prepare --run-dir examples/evaluation/a_plus_dedup/replay01",
        ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/a_plus_dedup/replay01 --batch primary",
        ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/a_plus_dedup/replay01 --batch repeats",
        ".\\.venv\\Scripts\\python.exe -B scripts/collect_agent_baseline.py --run-dir examples/evaluation/a_plus_dedup/replay01",
        "```", "",
        "完整记录在agent/results.jsonl，逐次语义核验在agent/reviews.json；原始CLI Trace与ToolResponse在agent/sessions。判断只使用实际可见证据，没有向模型补充gold。",
        "本实验小样本、模型服务默认采样未固定，其他不含重复的用例波动不能断言是去重带来的因果改善。全部历史结果保持原样，不提交或推送Git。"]
with (EXPERIMENT / "summary.md").open("x", encoding="utf-8") as f:
    f.write("\n".join(doc) + "\n")
write(EXPERIMENT / "final_manifest.json", {"name":"A＋去重", "before_sha256":sha(EXPERIMENT / "before.json"),
      "source_sha256":sha(ROOT / "src/enterprise_qa_agent/knowledge.py"),
      "business_pass":sum(r["review"]["business_pass"] for r in rows),
      "execution_and_business_pass":sum(r["execution_and_business_pass"] for r in rows),
      "budget_incomplete_runs":[r["run_id"] for r in rows if r["execution_status"] == "incomplete"],
      "result_count":len(rows), "gold_unchanged_sha256":sha(BASELINE / "gold.json")})
print((EXPERIMENT / "final_manifest.json").read_text(encoding="utf-8"))
