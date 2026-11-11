"""Recover guard-rejected launches only; never retry a model outcome."""
import json
import agent_baseline as base
from coverage_experiment import OUT

folder=OUT/"B_launcher_recovery"
base.prepare(folder)
plan=base.read(folder/"plan.json")
ids=["C13","M01","E03","F01"]
for identifier in ids:
    original=OUT/"B/sessions"/(identifier+"_r1")
    assert not list(original.rglob("traces/*.json")) if original.exists() else True
plan["cases"]=[c for c in plan["cases"] if c["case_id"] in ids]
plan["runs"]=[dict(run_id=c+"_r1",case_id=c,repeat=1,batch="recovery") for c in ids]
(folder/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
m=base.read(folder/"manifest.json")
m.update(plan_sha256=base.sha(folder/"plan.json"),case_count=4,session_count=4,user_turn_count=5)
(folder/"manifest.json").write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding="utf-8")
base.write(folder/"experiment_config.json",dict(name="B启动保护恢复",retrieval_mode="original",demand_rewrite=True,
           reason="README transient edit triggered hash guard before model calls; original launcher failures retained", replaces_model_outcome=False))
