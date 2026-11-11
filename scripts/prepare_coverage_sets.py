"""Freeze new coverage experiment plans before running any models."""
import json
from coverage_experiment import OUT
import agent_baseline as base
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=base.Path, default=OUT)
args = parser.parse_args()
OUT = args.root.resolve()
OUT.mkdir(parents=True, exist_ok=True)

def replace_plan(folder, cases, runs):
    plan = base.read(folder / "plan.json")
    plan["cases"], plan["runs"] = cases, runs
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = base.read(folder / "manifest.json")
    manifest["plan_sha256"] = base.sha(folder / "plan.json")
    manifest["case_count"] = len(cases)
    manifest["session_count"] = len(runs)
    manifest["user_turn_count"] = sum(len(c["messages"]) for c in cases)
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

for mode, name in [("original", "B"), ("dedup", "dedup_rewrite")]:
    folder = OUT / name
    base.prepare(folder)
    base.write(folder / "experiment_config.json", dict(name="B=A＋按需改写" if mode == "original" else "去重＋按需改写", retrieval_mode=mode, demand_rewrite=True))
pilot = OUT / "pilot_C11"
base.prepare(pilot)
p = base.read(pilot / "plan.json")
c = [c for c in p["cases"] if c["case_id"] == "C11"]
replace_plan(pilot, c, [dict(run_id=f"C11_r{n}", case_id="C11", repeat=n, batch="pilot") for n in [1,2,3]])
base.write(pilot / "experiment_config.json", dict(name="B重点先测", retrieval_mode="original", demand_rewrite=True, excluded_from_frozen_denominators=True))

themes = [
    ("DEV01", "员工培训报名截止时间和所需资料分别是什么？", "培训报名须在开课前10日完成。", "培训申请须上传主管确认函及结业测验记录。", ["培训", "报名"], ["培训", "申请"]),
    ("DEV02", "图书借阅需要满足什么条件，如何办理？", "企业图书馆仅向转正员工开放外借。", "图书借阅须登录资产门户登记书号，再到前台领取。", ["图书馆", "资格"], ["图书", "借阅"]),
    ("DEV03", "设备维修申请的时限和需要的资料是什么？", "设备维修应在发现故障后7日内申报。", "设备维修工单须填写序列号并附故障截图。", ["设备", "维修"], ["设备", "工单"]),
]
cases = []
for identifier, query, first, second, tags1, tags2 in themes:
    path = OUT / (identifier + ".json")
    docs = [dict(doc_id=f"{identifier}-{n}", title="内部服务说明", scope="全体员工", version="1", effective_from="2026-01-01", tags=tags,
                 sections=[dict(section_id=f"{identifier}-{n}-S1", text=text)]) for n, (text, tags) in enumerate([(first,tags1),(second,tags2)], 1)]
    base.write(path, docs)
    cases.append(dict(case_id=identifier, messages=[dict(role="user",content=query)], corpus=base.rel(path), corpus_sha256=base.sha(path),
                      necessary_evidence=[dict(doc_id=d["doc_id"],section_id=d["sections"][0]["section_id"]) for d in docs], simulate_failure=None,
                      expected="两项需求均按原文回答，无未给出的细则", development=True))
for name, mode in [("dev_B", "original"), ("dev_combo", "dedup")]:
    folder=OUT/name
    base.prepare(folder)
    replace_plan(folder,cases,[dict(run_id=c["case_id"]+"_r1",case_id=c["case_id"],repeat=1,batch="development") for c in cases])
    base.write(folder / "experiment_config.json",dict(name=name,retrieval_mode=mode,demand_rewrite=True,excluded_from_frozen_denominators=True))
