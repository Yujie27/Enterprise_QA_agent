"""Summarize frozen B observations and independent manual reviews, no model calls."""
import difflib
import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from statistics import mean
from coverage_experiment import OUT
import agent_baseline as base


def write(path, value):
    # Resume partial report generation only if the existing artifact is identical.
    if path.exists():
        assert base.read(path) == value, f"Refusing to overwrite different result: {path}"
    else:
        base.write(path, value)


def keys(payload):
    hits = list(payload.get("results", []))
    doc = payload.get("document")
    if doc:
        hits += [dict(doc_id=doc["doc_id"], **s) for s in doc["sections"]]
    return {f"{h['doc_id']}/{h['section_id']}" for h in hits}


def enrich(row):
    # Count only successful search returns here. Injected errors are a separate axis.
    seen = {}; queried = {}; row["no_new_successful_searches"] = 0
    row["exact_repeated_queries"] = 0
    row["search_error_attempts"] = 0
    row["post_coverage_reads"] = 0
    for step in row["steps"]:
        turn = step["turn"]
        observed = seen.setdefault(turn, set())
        queries = queried.setdefault(turn, set())
        payload = step["complete_return"]
        visible = keys(payload)
        if step["type"] == "tool_call":
            if step["tool"] == "search_docs":
                query = step["arguments"]["query"]
                row["exact_repeated_queries"] += query in queries
                if payload.get("error"):
                    row["search_error_attempts"] += 1
                elif queries and not visible - observed:
                    row["no_new_successful_searches"] += 1
                queries.add(query)
            elif step["required_evidence_complete_before_call"]:
                row["post_coverage_reads"] += 1
        observed.update(visible)
    return row


def aggregate(rows):
    evidence = [r for r in rows if r["required"]]
    scored = [r for r in rows if not r["review"].get("annotation_uncertainty")]
    deficits = [r for r in evidence if r["first_recall"] < 1]
    conflicts = [r for r in rows if r["case_id"] in {"C01", "C05", "C12", "C13"}]
    return dict(runs=len(rows), business_denominator=len(scored),
        business_pass=sum(r["review"]["strict_business_pass"] for r in scored),
        completed_and_business_pass=sum(r["review"]["completed_and_business_pass"] for r in scored),
        safe_terminal_and_business_pass=sum(r["review"]["safe_terminal_and_business_pass"] for r in scored),
        evidence_denominator=len(evidence), first_recall_macro=mean(r["first_recall"] for r in evidence),
        cumulative_recall_macro=mean(r["cumulative_recall"] for r in evidence),
        first_complete=sum(r["first_recall"] == 1 for r in evidence),
        cumulative_complete=sum(r["cumulative_recall"] == 1 for r in evidence),
        deficit_runs=len(deficits), recovered_after_first=sum(r["recovered_after_first"] for r in deficits),
        conflict_complete=sum(not r["missing"] for r in conflicts), conflict_denominator=len(conflicts),
        tool_calls=sum(r["tool_calls"] for r in rows),
        underlying_queries=sum(r["underlying_queries"] for r in rows),
        search_error_attempts=sum(r["search_error_attempts"] for r in rows),
        no_new_successful_searches=sum(r["no_new_successful_searches"] for r in rows),
        exact_repeated_queries=sum(r["exact_repeated_queries"] for r in rows),
        budget_rejections=sum(r["budget_rejections"] for r in rows),
        fifth_after_evidence_complete=sum(r["fifth_after_evidence_complete"] for r in rows),
        post_coverage_reads=sum(r["post_coverage_reads"] for r in rows),
        unsupported_assertion_runs=sum(bool(r["review"]["unsupported_assertions"]) for r in rows),
        statuses=dict(Counter(r["status"] for r in rows)))


def historical(folder):
    old = [json.loads(s) for s in (folder / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = []
    for item in old:
        steps = []
        prior = set(); required = set(item["necessary_evidence_keys"])
        for step in item["tool_steps"]:
            payload = step["full_tool_return"]
            steps.append(dict(turn=step["turn"], step=step["step"], tool=step["tool"],
                type="tool_call" if step["executed"] else "limit", arguments=step["arguments"],
                complete_return=payload, required_evidence_complete_before_call=bool(required and required <= prior)))
            prior.update(keys(payload))
        review = item.get("manual_review") or item["review"]
        passed = review.get("strict_pass", review.get("business_pass"))
        unsupported = review.get("unsupported_claims", [review["unsupported_quote"]] if review.get("unsupported_quote") else [])
        status = item["execution_status"]
        first_hits = item["first_agent_search_necessary_hit"]
        # Stored hit fields are lists of canonical doc/section keys.
        first = len(first_hits) / len(required) if required else None
        cumulative = (len(required) - len(item["missing_necessary_evidence"])) / len(required) if required else None
        rows.append(enrich(dict(run_id=item["run_id"],case_id=item["case_id"],required=sorted(required),
            steps=steps,missing=item["missing_necessary_evidence"],first_recall=first,cumulative_recall=cumulative,
            recovered_after_first=bool(required and first < 1 and cumulative == 1),status=status,
            tool_calls=item["tool_calls"],underlying_queries=sum(s["type"]=="tool_call" and s["tool"]=="search_docs" and not s["complete_return"].get("error") for s in steps),
            budget_rejections=sum(s["type"]=="limit" for s in steps),
            fifth_after_evidence_complete=sum(s["type"]=="limit" and s["required_evidence_complete_before_call"] for s in steps),
            review=dict(strict_business_pass=passed, completed_and_business_pass=passed and status=="completed",
                safe_terminal_and_business_pass=passed and status in {"completed","insufficient_evidence","tool_error"},
                unsupported_assertions=unsupported)) ))
    return rows


def pct(n): return f"{n:.2%}"
def link(row): return str(Path(row["trace"]).relative_to(Path(base.rel(OUT)))).replace("\\", "/")


def main():
    rows = [json.loads(s) for s in (OUT/"observations.jsonl").read_text(encoding="utf-8").splitlines()]
    reviews = {(r["config"],r["run_id"]):r for r in base.read(OUT/"reviews.json")["reviews"]}
    groups = {}
    for row in rows:
        row["review"] = reviews[row["config"],row["run_id"]]
        enrich(row)
        groups.setdefault(row["config"],[]).append(row)
        path = OUT/"per_run"/row["config"]
        path.mkdir(parents=True,exist_ok=True)
        write(path/(row["run_id"]+".json"),row)
    content="".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows)
    if (OUT/"results.jsonl").exists():
        assert (OUT/"results.jsonl").read_text(encoding="utf-8")==content
    else:
        with (OUT/"results.jsonl").open("x",encoding="utf-8") as f: f.write(content)
    old_groups = {"A":historical(base.ROOT/"examples/evaluation/agent_baseline/20261110_original_agent_v020"),
                  "A_plus_dedup":historical(base.ROOT/"examples/evaluation/a_plus_dedup/20261110_v020/agent")}
    metrics = {name:aggregate(group) for name,group in {**old_groups,**groups}.items()}
    write(OUT/"metrics.json",metrics)
    configuration = base.read(OUT/"B/manifest.json")["model_config"]
    for name in ["B","dedup_rewrite","pilot_C11","B_launcher_recovery","dev_B","dev_combo"]:
        base.check(OUT/name)
    assert configuration == base.read(OUT/"before.json")["model_config"]
    assert base.read(OUT/"B/plan.json")["cases"] == base.read(OUT/"dedup_rewrite/plan.json")["cases"]
    assert base.read(OUT/"B/plan.json")["runs"] == base.read(OUT/"dedup_rewrite/plan.json")["runs"]
    write(OUT/"config_matrix.json",dict(shared_model_config=configuration, gold_sha256=base.sha(base.BASELINE/"gold.json"),
        configurations=[dict(name=n,retrieval_mode=mode,demand_rewrite=enabled) for n,mode,enabled in
                        [("A","original",False),("A＋去重与来源呈现","dedup",False),("B=A＋按需改写","original",True),("去重＋按需改写","dedup",True)]],
        batch_note="same 12 scenarios and 18 trials each; pilot3 and development6 excluded; B4 pre-model launch failures retained and executed in recovery folder"))
    before=base.read(OUT/"before.json")
    assert all(base.sha(base.ROOT/p)==h for p,h in before["historical_hashes"].items())
    assert all(base.sha(OUT/"sealed_a_dedup"/p)==h for p,h in before["source_hashes"].items())
    source_hashes={}
    diff=[]
    for file in (base.ROOT/"src").rglob("*.py"):
        target=OUT/"evaluated_source"/file.relative_to(base.ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(file.read_bytes())
        source_hashes[base.rel(file)]=base.sha(file)
        prior=OUT/"sealed_a_dedup"/file.relative_to(base.ROOT)
        diff += list(difflib.unified_diff(prior.read_text(encoding="utf-8").splitlines(True),file.read_text(encoding="utf-8").splitlines(True),
                fromfile="A+dedup/"+base.rel(file),tofile="B/"+base.rel(file)))
    (OUT/"b_changes.patch").write_text("".join(diff),encoding="utf-8")
    (OUT/"worktree_after.patch").write_bytes(subprocess.check_output(["git","diff","HEAD","--binary"],cwd=base.ROOT))
    audit=dict(commit=base.git("rev-parse","HEAD"),branch=base.git("branch","--show-current"),
        historical_files_verified=len(before["historical_hashes"]),historical_changed=[],source_hashes=source_hashes,
        model_configuration_equal=True,frozen_cases_equal=True,frozen_gold_sha256=base.sha(base.BASELINE/"gold.json"),
        git_staged_diff=base.git("diff","--cached","--stat"),worktree=base.git("status","--short"),
        scripts={base.rel(p):base.sha(p) for p in (base.ROOT/"scripts").glob("*coverage*.py")},
        no_commit_or_push=True)
    # Credential comparison is local; never emit the secret or any matching content.
    secret=os.getenv("OPENAI_API_KEY","")
    if len(secret)>8:
        assert not any(secret.encode() in p.read_bytes() for p in OUT.rglob("*") if p.is_file())
    audit["configured_credential_absent_from_experiment_files"]=True if len(secret)>8 else "not checked"
    write(OUT/"audit.json",audit)

    lines=["# B：基于证据覆盖缺口的按需查询改写", "",
        "本轮实现和评测已完成，但**没有证明C11证据覆盖稳定性提高**。B与组合的C11都仅1/3完整；主实验无第五次请求，先测仍发生1次。代码不据结果二次调参。", "",
        "## 条件、版本与记录", "",
        f"commit `{audit['commit']}`，分支 `{audit['branch']}`；版本仍0.2.0，用独立实验开关区分。模型deepseek-flash，原端点及采样默认值、k默认5、工具每轮4/max_iters5、非并行请求参数不变，详见[配置矩阵](config_matrix.json)。模型仍能自主设置limit（本次5/8/10都有），默认值没有提高。",
        "原版A、去重、B、组合均有显式配置；关闭按需改写后提示词和工具schema与封存版相等，原版检索108条冻结输出一致。[实现与复现](code_notes.md)；[封存前清单](before.json)、[B相对去重差异](b_changes.patch)、[已测源码](evaluated_source/src/enterprise_qa_agent)、[最终审计](audit.json)。",
        f"历史{audit['historical_files_verified']}个文件逐字节哈希复核未改，语料和gold未改。AGENTS.md未在仓库发现。未提交或推送Git。运行日期为2026-11-10，报告整理2026-11-11，目录名沿用启动时标识。", "",
        "两种配置均12场景、18真实会话（19用户轮次）；另C11先测3次、开发题6次，总45次真实运行，无Mock、无模型不可用。普通用例独立，M01复用会话。",
        "启动异常：误改README触发冻结保护，B的C13_r1/M01/E03/F01在模型前拒绝，恢复README原字节后只补执行这4条于B_launcher_recovery。保留[4条失败索引](launch_failures.json)及B/launcher原stderr；不算额外模型试验或挑选成功样本。其余未启动批次随后照原计划执行。", "",
        "## 指标定义", "",
        "必要证据为冻结gold的原始doc_id/section_id；M01、E03沿用原Agent计划补充的D02、D01入口。每组18中R06/F01两题无必要条款，排除证据覆盖分母，故16；不是把空gold当作负例。M01累计可见包含前轮上下文。",
        "首次覆盖=Agent自己第一次search返回（不是原始用户问题的直接k=5）；累计覆盖=所有实际成功工具返回的并集。宏Recall逐运行平均，完整覆盖要求所有必要条款，冲突双方都到齐；副本不能当原件或增加分数。缺口恢复=首次不完整的运行中，后续实际工具使必要证据完整；它本身不等于业务通过。",
        "业务通过沿用固定判据：目标完整、引用支持、缺口正确、无无依据制度断言。安全部分答案可能仍不完整。复核由助手逐条阅读实际返回和conversation完成，非自动裁判或额外模型评审，详见[45条复核](reviews.json)，建议候选人复审。",
        "正常结束且通过主列沿用历史严格口径status=completed；另列安全终止且通过，包括明确资料不足的insufficient_evidence和预期故障tool_error。这样不把安全拒答当框架异常，也不将incomplete当已完成。",
        "无新增搜索=同轮首次search之后，成功search未增加doc/section键；空返回也算，读原文和错误重试不混入。新ID不保证语义新证据。与observations中的原始no_new_repeat_searches不同：该旧采集字段含故障重试，本报告用results中的no_new_successful_searches。所有底层search一次一个query，未用批量；读原文独立占预算。", "",
        "## 主实验对照", "",
        "|配置|首搜Recall/完整|累计Recall/完整|缺口恢复|冲突完整|业务通过|completed且通过|安全终止且通过|",
        "|---|---|---|---|---|---|---|---|"]
    for name in ["A","A_plus_dedup","B","dedup_rewrite"]:
        m=metrics[name]
        lines.append(f"|{name}|{pct(m['first_recall_macro'])}；{m['first_complete']}/{m['evidence_denominator']}|{pct(m['cumulative_recall_macro'])}；{m['cumulative_complete']}/{m['evidence_denominator']}|{m['recovered_after_first']}/{m['deficit_runs']}|{m['conflict_complete']}/{m['conflict_denominator']}|{m['business_pass']}/18|{m['completed_and_business_pass']}/18|{m['safe_terminal_and_business_pass']}/18|")
    lines += ["", "A和A＋去重来自历史真实记录，保留当时人工判定，费用/覆盖统计按相同公式重新计算到新metrics.json，未改旧文件。重复难题加权，18不是18个独立题，不做显著性推断。", "",
        "[逐场景对照与直接证据索引](comparison_details.md)列出12个场景的通过数及C13、E03、F01、M01的实际记录。先测清单user_turn_count字段存在计数勘误，原值和实际3次单轮说明见[manifest_errata.json](manifest_errata.json)，不修改冻结清单。", "",
        "|配置|获准工具|实际底层查询|搜索错误尝试|无新增成功搜索|完全相同查询重复|预算拒绝|充分证据后第5次|无依据断言运行|状态|",
        "|---|---|---|---|---|---|---|---|---|---|"]
    for name in ["A","A_plus_dedup","B","dedup_rewrite","pilot_C11","dev_B","dev_combo"]:
        m=metrics[name]
        lines.append(f"|{name}|{m['tool_calls']}|{m['underlying_queries']}|{m['search_error_attempts']}|{m['no_new_successful_searches']}|{m['exact_repeated_queries']}|{m['budget_rejections']}|{m['fifth_after_evidence_complete']}|{m['unsupported_assertion_runs']}|{m['statuses']}|")
    lines += ["", "post_coverage_reads是证据齐全后的读取计数（见metrics），不能全部当无效追查：冲突核验仍应读取；简单C11的额外读取另逐条讨论。F01每组2次搜索工具尝试，但错误在KnowledgeBase.search前注入，底层查询为0。", "",
        "## C11：逐次查询、证据到达、无新增及预算", "",
        "|组/运行|实际搜索序列（模型自主）|期限首次到达|材料首次到达|无新增搜索|第5次拒绝|业务/状态|Trace|",
        "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        if row["case_id"]!="C11": continue
        def at(key):
            a=row["acquired_at"].get(key)
            return f"turn{a['turn']}/step{a['step']}" if a else "未取得"
        lines.append(f"|{row['config']}/{row['run_id']}|{' → '.join(row['queries'])}|{at('D01/D01-S1')}|{at('D04/D04-S1')}|{row['no_new_successful_searches']}|{row['budget_rejections']}|{row['review']['strict_business_pass']}/{row['status']}|[记录]({link(row)})|")
    lines += ["", "先测3条单列：证据2/3、业务2/3、completed且业务1/3；C11_r2在第四步取得D04后还请求第五次read(D04)，充分检索片段已经可见仍触顶。先测后未改业务代码或提示词。",
        "B主实验与组合均首搜0/3完整、后续1/3完整，业务1/3；各恢复成功均第二步‘费用报销…’查询实际取得D04，之后仍读D01/D04。A历史C11证据1/3但业务0/3（附次日起算）；A＋去重证据/业务3/3但completed且业务1/3。当前组合没有保持去重轮C11的偶发3/3，应如实记退化，不能说新策略稳定改善。",
        "词项原因仍在：knowledge.py保持中文二元组和至少2重叠门槛，searchable只有title/text/tags。失败的‘报销 发票 凭证…’缺少D04所需的足够匹配，实际只回D01或空；加入‘费用报销’的自主查询取得D04。没有补材料→票据词表，也没有降低门槛。公开needs多能列对，covered可能在连续工具请求间滞后，识别需求不等于正确更新证据。", "",
        "## C13与其他退化", "",
        "B三次首搜均COPY0—4/15日，D01/30日累计0/3；r2追溯D02仍只有15日一方。组合三次首搜都直接取得D01和D02、读取双方并请求确认，完整覆盖3/3。改善链路来自去重释放候选位置，与此前A＋去重一致，不能把全部收益归于按需改写。",
        "组合C13_r1/r2来源描述由真实source_info支持；r3主冲突结论也对，但额外说‘通用范围’及‘适用范围相同’，实际scope是未提供，严格业务记失败（2/3），并非召回失败。详见对应per_run及Trace。没有出现先按15日的无依据建议。",
        "C01三次、C05两组均列双方、核原文并请求依据，本次没有先选15日；这属于回答行为波动，不能把非重复资料题的所有差异归因去重或改写。C01组合r1引文省略‘费用’二字，起算含义仍支持，记逐字引用瑕疵。C12两section均保留；‘同范围’措辞有风险，但同时明确范围未标，不据此裁决。",
        "E03两组均两次空返回，安全保留日历含义未知，无具体执行建议；但均未取得D01，入口覆盖相对两份历史记录退化，不宣称核验了具体制度原文。F01都真实触发两次故障且明确区分失败/不存在，没有编造UTC时间。M01分别1/2次工具、第二轮均正确继承研发差旅上下文。R01/C02单证据仍正常；R07可见scope并使用解释，但未做改号/顺序因果对照。", "",
        "## 独立开发题", "",
        "3份新资料为培训‘期限＋资料’、借阅‘条件＋流程’、设备维修‘期限＋资料’，不使用报销/票据措辞；输入和必要键在dev_B/dev_combo各自plan.json，资料DEV01—03.json。均未进入18次冻结分母。",
        "|组/题|首搜→累计Recall|业务判定|说明及Trace|", "|---|---|---|---|"]
    for row in rows:
        if not row["config"].startswith("dev_"): continue
        lines.append(f"|{row['config']}/{row['case_id']}|{pct(row['first_recall'])}→{pct(row['cumulative_recall'])}|{row['review']['strict_business_pass']}|{row['review']['reason']} [记录]({link(row)})|")
    lines += ["", "DEV01的培训报名/培训申请环节未明确等价，业务总指标剔除该题（不反改资料或gold），仍报告证据覆盖：B三题累计3/3，组合1/3。剔除后的开发业务B=2/2、组合=1/2；不是稳定性结论。B的DEV01有据限定环节，保留其逐条通过判定供复核。",
        "组合DEV02覆盖表已写缺条件，但只读流程即结束，并用流程文档的全体员工scope替代资格判断；转正资格未见，安全限定不足，失败。B的DEV02实际第二搜恢复资格，但顺带扩搜期限/册数，仍有需求扩张。组合DEV03首搜已有两证据，仅1次工具即答，展示简单片段足够后结束；B同题仍用3次。", "",
        "## 机制边界与后续方向", "",
        "本轮是模型覆盖表＋程序新证据统计＋按需策略提示的增量实现。没有程序语义裁判或硬性覆盖状态机，coverage是模型公开自述（validated_semantically=false），程序只计真实ID/原文新颖度及底层查询数；不生成私有思维。可观察到按缺口改写，也可观察到表滞后、流程代条件、证据够仍读取。不能把机制实现写成所有行为要求已被可靠保证。",
        "优先问题：①C11词汇恢复仍不稳定，需独立验证更可靠的缺口查询生成/语义覆盖更新；②简单问题停止策略与证据记忆仍弱，先测多余第五次及开发题假覆盖都未消除；③独立的冲突来源补查和回答依据约束仍需要后续C/D/G设计，尤其未提供scope不能扩成通用范围。本轮未加入这些修复，未做scope加权、主动冲突来源补查或断言验证。",
        "样本很小、模型别名和默认采样可能变化，无固定seed，无配对相同随机数。先测/主测/开发严格分开；两份历史基线跨批采样，不能用总通过差值证明因果改善。无新增ID指标不是语义重复率；程序金标准只在事后评估，未传给Agent。最终答案和错误表述均原样保留，完整工具返回见各sessions/tool_returns.json，逐条汇总见[results.jsonl](results.jsonl)、[Trace索引](trace_index.md)、[机器指标](metrics.json)。", ""]
    (OUT/"summary.md").write_text("\n".join(lines),encoding="utf-8")
    index=["# 全部45次真实运行与Trace", "", "|配置|运行|状态|工具|业务|结果|Trace|", "|---|---|---|---|---|---|---|"]
    for r in rows:
        index.append(f"|{r['config']}|{r['run_id']}|{r['status']}|{r['tool_calls']}|{r['review']['strict_business_pass']}|[完整结果](per_run/{r['config']}/{r['run_id']}.json)|[Trace]({link(r)})|")
    (OUT/"trace_index.md").write_text("\n".join(index)+"\n",encoding="utf-8")
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
