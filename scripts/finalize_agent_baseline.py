"""Validate trace-bound semantic reviews and publish an append-only report."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from agent_baseline import check, now, read, rel, sha, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    manifest = check(folder)
    collection = read(folder / "collection_manifest.json")
    assert sha(folder / "observations.jsonl") == collection["observations_sha256"]
    observations = [json.loads(line) for line in (folder / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
    review_document = read(folder / "reviews.json")
    reviews = {r["run_id"]: r for r in review_document["reviews"]}
    assert len(reviews) == len(observations) == 18
    assert set(reviews) == {r["run_id"] for r in observations}
    rows = []
    for observation in observations:
        review = reviews[observation["run_id"]]
        for citation in review["citations"]:
            assert citation["key"] in observation["actually_visible_evidence"], f"Citation never visible: {observation['run_id']}"
        for unsupported in review["unsupported_claims"]:
            assert unsupported["quote"] in observation["final_answer"], f"Review quote not in final answer: {observation['run_id']}"
        row = dict(observation, manual_review=review)
        rows.append(row)
    (folder / "per_run").mkdir(exist_ok=False)
    with (folder / "results.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            write(folder / "per_run" / f"{row['run_id']}.json", row)
    counts = {
        "distinct_cases": len({r["case_id"] for r in rows}), "sessions": len(rows),
        "user_turns": sum(len(r["messages"]) for r in rows),
        "real_attempts": sum(bool(r["model_reply_metadata"]) for r in rows),
        "not_executed": sum(r["execution"] and r["execution"]["execution"] == "not_executed" for r in rows),
        "strict_pass": sum(r["manual_review"]["strict_pass"] for r in rows),
        "primary_strict_pass": sum(r["manual_review"]["strict_pass"] for r in rows if r["repeat"] == 1),
        "execution_status": dict(Counter(r["execution_status"] for r in rows)),
        "tool_calls": sum(r["tool_calls"] or 0 for r in rows),
        "budget_rejected_requests": sum(len(r["budget_rejected_requests"]) for r in rows),
        "watchdog_timeouts": sum(r["launcher"]["watchdog_timeout"] for r in rows),
        "framework_finished_reasons": dict(Counter(m["finished_reason"] for r in rows for m in r["model_reply_metadata"])),
        "labels_not_mutually_exclusive": dict(Counter(label for r in rows for label in r["manual_review"]["labels"])),
    }
    groups = {}
    for case_id in ["C01", "C11", "C13"]:
        members = [r for r in rows if r["case_id"] == case_id]
        groups[case_id] = {
            "attempts": len(members), "strict_pass": sum(r["manual_review"]["strict_pass"] for r in members),
            "all_evidence_visible": sum(bool(r["all_visible_complete"]) for r in members),
            "recovered_vs_raw_query_k5": sum(bool(r["recovered_vs_raw_query_k5"]) for r in members),
            "later_recovery_after_first_agent_search": sum(bool(r["recovered_after_agent_first_search"]) for r in members),
        }
    root = Path(__file__).resolve().parents[1]
    trace_link = lambda r: Path(r["trace_path"]).relative_to(Path(rel(folder))).as_posix() if r["trace_path"] else ""
    doc = ["# 原版完整 Agent 重点场景基线", "",
           f"分支 `{manifest['branch']}`；commit `{manifest['commit_sha']}`；业务代码 v0.2.0。",
           "", "## 固定条件和测量边界", "",
           "模型配置：`deepseek-flash`，本地OpenAI兼容接口，非流式；temperature/top_p/seed未显式设置，沿用服务默认值。完整非敏感配置、依赖版本和端点origin见manifest.json，不保存密钥。",
           "每轮4次工具调用，框架max_iters=5。模型可自主设置search的limit、查询和读取对象，运行器不指定路径。每场景独立子进程/会话，M01由原CLI的interactive+follow-up复用Agent实例。最多两个独立进程并发。",
           "执行原版cli.main；外部日志观察器调用原_tool_response、原Agent.reply，返回原对象不变，记录完整工具响应（包括拒绝/错误）、回复usage和finished_reason。原始CLI Trace完整保留；不保存私有思维内容。",
           "开始时保留上一轮未跟踪的scripts和examples/evaluation，tracked diff为空。manifest固定了原检索基线全目录及业务代码/资料哈希；执行及最终审计均确认未改变。没有修改src、提示词、同义词、语料、依赖、预算配置文件，没有提交或推送。",
           "", "## 总体结果与分母", "",
           f"- 12个场景均执行，0个未执行。首轮12次，C01/C11/C13各追加2次，总计{counts['sessions']}次真实运行、{counts['user_turns']}轮用户输入、{counts['tool_calls']}次获准工具调用。没有Mock、预算追加或挑选成功运行。",
           f"- 严格业务通过：首轮{counts['primary_strict_pass']}/12；全部{counts['strict_pass']}/18。完整性、引用与无附带无依据断言都需满足；仅主结论正确不算严格通过。难题重复加权，不把18次视为独立样本或泛化准确率。",
           f"- 执行状态：{counts['execution_status']}；框架回复结束原因：{counts['framework_finished_reasons']}。F01的tool_error为预期注入路径，业务正确说明错误时可通过。",
           f"- 预算拒绝{counts['budget_rejected_requests']}次，外部900秒watchdog超时{counts['watchdog_timeouts']}次；有4/4用尽但正常结束的运行，不能仅据调用数等于4判预算不足。",
           "- 业务判定为助手逐条阅读实际返回与回答的语义复核，规则在plan.json先行固定，无额外裁判API调用；候选人可继续审阅reviews.json。",
           "", "## 逐次业务结果和 Trace 索引", "",
           "|运行|执行状态|工具数|完整必要证据可见|业务严格通过|业务结论|Trace|", "|---|---|---|---|---|---|---|"]
    for row in rows:
        complete = "不适用" if row["all_visible_complete"] is None else "是" if row["all_visible_complete"] else "否"
        doc.append(f"|{row['run_id']}|{row['execution_status']}|{row['tool_calls']}|{complete}|{'是' if row['manual_review']['strict_pass'] else '否'}|{row['manual_review']['business_status']}|[记录]({trace_link(row)})|")
    doc += ["", "每条结果的per_run/*.json和results.jsonl包含输入、实际参数、完整返回、公开动作理由、可见证据、最终回答、引用核验、资料缺口、执行/业务状态与分类。sessions/*/tool_returns.json为原ToolResponse对象序列及实际payload；launcher包含原CLI控制台输出。",
            "", "## 重复运行差异：恢复不等于答案全部正确", "",
            "|场景|严格通过|必要原始证据最终完整可见|相对原问题k=5恢复|Agent首次搜索后再恢复|", "|---|---|---|---|---|"]
    for case_id, group in groups.items():
        doc.append(f"|{case_id}|{group['strict_pass']}/3|{group['all_evidence_visible']}/3|{group['recovered_vs_raw_query_k5']}/3|{group['later_recovery_after_first_agent_search']}/3|")
    doc += ["", "### C11：1/3恢复证据，0/3严格业务通过", "",
            "[C11_r1](per_run/C11_r1.json)：先搜“报销期限 报销所需材料”，再搜“报销 提交材料 发票 凭证 清单”，均只有D01，之后读取D01；据此答30日并如实说材料无法确认。安全但没有恢复D04。",
            "[C11_r2](per_run/C11_r2.json)：首次由模型自主写出“费用报销期限 报销所需材料”，即返回D01-S1与D04-S1；后续另搜并读取两份。相比原始问题k=5的缺证据已恢复，但不是模型首次搜索失败后的后续恢复。答案引用30日、合规票据正确，另添加“费用的发生次日开始计算”，实际原文没有第0日/次日起算定义，因此严格不通过。",
            "[C11_r3](per_run/C11_r3.json)：首搜只得D01，读取后再用“报销 提交材料 发票 凭证 单据 清单”，仍只得D01；材料缺口如实保留。没有把全库D04补进模型上下文。",
            "因此自主改写能偶尔恢复原始单检索的词项缺口，但在固定预算内并不稳定，且恢复证据与回答约束是两项独立问题。",
            "", "### C13：3/3都缺30日方，识别副本没有自动带来冲突覆盖", "",
            "[C13_r1](per_run/C13_r1.json)、[C13_r2](per_run/C13_r2.json)、[C13_r3](per_run/C13_r3.json)的首次搜索limit均为5，全部返回COPY0—4/15日，没有D01/30日；读取COPY0后模型看到copied_from=D02，自主读取D02得到原始15日规则。r2额外改写搜索也仍只有副本。",
            "三次均回答15日并说明证据范围，未取得30日冲突方。本轮应分类为检索缺证据且模型未恢复，不能说模型看见30/15冲突后仍任意裁决，也不能把副本的数量当独立证据。",
            "r3还说COPY0—4“均标注为复制自D02”；实际上只有read(COPY0)暴露该标注，COPY1—4的search返回没有copied_from。全库确有该字段不等于本次模型看见，故记录次要的来源标注扩张。",
            "", "### C01/C05：冲突证据可见后仍可能给出无来源执行建议", "",
            "C01三次都取得两条证据并读取双方；[r1](per_run/C01_r1.json)和[r3](per_run/C01_r3.json)并列冲突、请求确认，没有自行选数。",
            "[C01_r2](per_run/C01_r2.json)虽然说明无法唯一确定，却追加“建议按更严格的15日期限操作”；[C05_r1](per_run/C05_r1.json)虽然没有仅凭新日期选D02，却追加“按较严格口径（费用发生后15日内）备妥材料”。按预先固定的依据约束，即使声明只是风险建议，也不能使这些执行口径获得来源支持。主结论正确、引用条款正确，严格业务仍不通过；这不是召回失败。",
            "", "### R07、E03、F01、M01", "",
            "- [R07_r1](per_run/R07_r1.json)：实际返回研发D01和销售D02，公开理由点明scope，读取双方后依据研发scope回答返程15日，未因数字不同就判同范围冲突。能观察到scope使用的解释与行为；没有改号/顺序对照，不能因果证明模型完全不依赖编号或排名。",
            "- [E03_r1](per_run/E03_r1.json)：首次搜“30日 工作日 自然日 计算”为空，第二次改写得到D01，再读原文并查定义；明确日的口径未提供，未建议按自然日或工作日执行。属于Agent首次失败后自主恢复证据，最终仍合理说明资料不足。此前原检索基线没有E03，不能伪造前后原问题Recall对比。",
            "- [F01_r1](per_run/F01_r1.json)：两次search均为原开关注入的RuntimeError，故障路径实际触发；明确工具失败、未能核实期限，没有说制度不存在，也没有引用实际未取得的single.json中的30日。",
            "- [M01_r1](per_run/M01_r1.json)：第一轮search+read(D01)+read(D02)共3次，按范围列选项；第二轮对“研发部门，差旅报销。”无需新工具，直接结合本会话已读D02回答返程15日。每轮证据不能只看第二轮是否重新读取。",
            "", "## 失败/恢复分类（可多选）", "",
            "|分类|运行数|说明|", "|---|---|---|"]
    details = {
        "必要证据未召回，模型未恢复": "C11_r1/r3、C13_r1/r2/r3；5次。安全表达资料不足也可能未完成目标。",
        "首次未召回，但模型通过后续动作恢复": "C11_r2是相对原问题k=5由首次自主改写恢复；E03_r1是Agent首次搜索后再恢复。两种轴分开保存，不合成统一恢复率。",
        "必要证据已可见，模型仍判断错误": "本轮未发现把已见双方直接错误裁决为单一期限的主结论；附带执行建议列下一类。",
        "主答案正确，但引用错误或附带无依据断言": "C05_r1、C01_r2、C11_r2，以及C13_r3的局部15日答案附带来源标注扩张；后者整体证据依然不完整。",
        "工程异常、预算不足或路径未触发": "本轮没有程序崩溃、预算拒绝、框架迭代耗尽或F01路径未触发。预期tool_error单独记。",
    }
    for label, detail in details.items():
        doc.append(f"|{label}|{counts['labels_not_mutually_exclusive'].get(label, 0)}|{detail}|")
    doc += ["", "## 下一轮B1/B2应解决什么（仅建议，未实施）", "",
            "本报告把B1定义为“查询/初始检索的证据获取改进”，B2定义为“相关或冲突证据补查、来源多样性与证据约束回答”，避免未定义缩写造成误解。",
            "- **B1：稳定取得多意图问题的全部证据**。依据C11三次：r1/r3自主换发票/凭证等词仍失败，r2加“费用报销”后首搜即可取得D04。下一轮应固定语料/预算，比较业务词汇或多意图检索的稳定性，不把单次模型恰好写对词当作检索已解决，也不直接提高预算覆盖原记录。",
            "- **B2：补查另一独立来源，而不仅追溯同一来源副本**。依据C13三次：COPY0→D02的追溯均成功，但D01/30日始终缺失。应验证来源折叠和冲突关联补查能否在4次预算内增加30日证据覆盖；R01/C02单证据对照必须继续允许有据回答，不能一律假定隐藏冲突而拒答。",
            "- **B2同时约束已取得证据后的回答**。C01_r2/C05_r1不能靠增加召回修复其“先按15日操作”建议；C11_r2也已经取得全部证据，却补造次日起算。应独立评估引用/附带断言和缺口说明，避免把证据Recall提高直接等同业务成功。",
            "", "## 重现与限制", "",
            "保存了真实原始Trace而非预设动作日志；采集代码位于scripts/agent_baseline.py，整理和语义核验在collect_agent_baseline.py、reviews.json、finalize_agent_baseline.py。可用新目录重跑，拒绝覆盖原目录。",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py prepare --run-dir examples/evaluation/agent_baseline/replay01",
            ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/agent_baseline/replay01 --batch primary",
            ".\\.venv\\Scripts\\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/agent_baseline/replay01 --batch repeats",
            ".\\.venv\\Scripts\\python.exe -B scripts/collect_agent_baseline.py --run-dir examples/evaluation/agent_baseline/replay01",
            "# 阅读新observations和Trace，独立编写新reviews.json；不要照搬本次判定",
            ".\\.venv\\Scripts\\python.exe -B scripts/finalize_agent_baseline.py --run-dir examples/evaluation/agent_baseline/replay01",
            "```", "",
            "仅12个定向场景，只有3题各重复3次，不能估计一般稳定性或统计显著性。服务默认采样参数/模型别名可能变化；并发2个独立会话可能有服务负载影响。本轮记录的是配置模型名与AgentScope报告的usage，不保证计费token或后端权重版本不变。",
            "单次原问题k=5、Agent首次自主查询和多步累计可见证据是不同条件，已分别记录。最终判定不靠完整语料替模型补证据。公开理由是模型自述，不能证明内部因果。",
            "R06/F01/E03的资料不足或故障说明可以是正确业务结果；completed不是答案必然可确定。预算恰好用满但未发生拒绝，不能推断更高预算一定改善。",
            "旧检索基线及业务代码保持原样；本轮只是测量，不实施B1/B2。"]
    with (folder / "summary.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(doc) + "\n")
    file_hashes = {rel(p): sha(p) for p in folder.rglob("*") if p.is_file()}
    write(folder / "assessment_manifest.json", {"finished_at_utc": now(), "counts": counts,
          "repeat_groups": groups, "finalizer_sha256": sha(__file__),
          "review_sha256": sha(folder / "reviews.json"), "artifacts_sha256": file_hashes,
          "protected_files_unchanged": True})
    print(json.dumps({"counts": counts, "repeat_groups": groups}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
