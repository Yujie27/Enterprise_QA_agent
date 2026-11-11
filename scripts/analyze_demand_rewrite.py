"""Collect B trials and compute observation-only coverage/cost statistics."""
import json
from pathlib import Path
from collections import Counter
from coverage_experiment import OUT
import agent_baseline as base


def gather(group, names):
    records = {}
    failures = []
    for name in names:
        folder = OUT / name
        base.check(folder)
        plan = base.read(folder / "plan.json")
        for item in plan["runs"]:
            session=folder/"sessions"/item["run_id"]
            traces=list((session/"traces").glob("*.json"))
            if not traces:
                failures.append(dict(folder=name,run_id=item["run_id"],stage="launcher_before_model",trace=None))
                continue
            assert item["run_id"] not in records
            trace=base.read(traces[0])
            case=next(c for c in plan["cases"] if c["case_id"]==item["case_id"])
            required={f"{e['doc_id']}/{e['section_id']}" for e in case["necessary_evidence"]}
            events=trace["events"]
            slots=[e for e in events if e["type"] in {"tool_call","limit"}]
            returns=base.read(session/"tool_returns.json")
            assert len(slots)==len(returns)
            seen=set(); first=None; acquired={}; turns={}; steps=[]; repeat_searches=0; searches=0
            for slot, ret in zip(slots,returns):
                payload=ret["payload_passed_to_original_tool_response"]
                parsed=json.loads(ret["returned_tool_response"]["content"][0]["text"])
                assert parsed==payload
                found=list(payload.get("results",[]))
                doc=payload.get("document")
                if doc:
                    found += [{**{k:v for k,v in doc.items() if k!="sections"},**s} for s in doc["sections"]]
                keys={f"{h['doc_id']}/{h['section_id']}" for h in found}
                turn_seen=turns.setdefault(slot["turn"],set())
                new=keys-turn_seen
                supported_before=bool(required) and required<=seen
                if slot["tool"]=="search_docs" and slot["type"]=="tool_call":
                    searches+=1
                    if first is None: first=set(keys)
                    if searches>1 and not new: repeat_searches+=1
                for key in keys:
                    acquired.setdefault(key,dict(turn=slot["turn"],step=slot["step"],tool=slot["tool"]))
                turn_seen.update(keys); seen.update(keys)
                steps.append(dict(**slot,complete_return=payload,visible_keys=sorted(keys),new_keys=sorted(new),
                                  required_evidence_complete_before_call=supported_before))
            row=dict(config=group,run_id=item["run_id"],case_id=item["case_id"],messages=case["messages"],
                     corpus=case["corpus"],corpus_sha256=case["corpus_sha256"],trace=base.rel(traces[0]),
                     status=trace["status"],answer=trace["answer"],conversation=trace.get("conversation"),
                     tool_calls=trace["tool_calls"],steps=steps,coverage_reports=[e for e in events if e["type"]=="coverage_report"],
                     acquired_at=acquired,required=sorted(required),missing=sorted(required-seen),
                     first_recall=len(required & (first or set()))/len(required) if required else None,
                     cumulative_recall=len(required & seen)/len(required) if required else None,
                     recovered_after_first=bool(required and not required<=(first or set()) and required<=seen),
                     first_query=next((s["arguments"]["query"] for s in steps if s["tool"]=="search_docs"),None),
                     queries=[s["arguments"]["query"] for s in steps if s["tool"]=="search_docs"],
                     no_new_repeat_searches=repeat_searches,search_tool_attempts=searches,
                     underlying_queries=sum(s["tool"]=="search_docs" and s["type"]=="tool_call" and not s["complete_return"].get("error") for s in steps),
                     budget_rejections=sum(s["type"]=="limit" for s in steps),
                     fifth_after_evidence_complete=sum(s["type"]=="limit" and s["required_evidence_complete_before_call"] for s in steps),
                     review=None)
            records[row["run_id"]]=row
    return list(records.values()), failures


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.root.resolve()
    groups={"pilot_C11":["pilot_C11"],"B":["B"],"dedup_rewrite":["dedup_rewrite"],"dev_B":["dev_B"],"dev_combo":["dev_combo"]}
    if (OUT / "B_launcher_recovery").exists():
        groups["B"].append("B_launcher_recovery")
    all_rows=[]; failed=[]
    for group,names in groups.items():
        rows,failures=gather(group,names)
        all_rows+=rows;failed+=failures
    assert len(all_rows)==45
    with (OUT/"observations.jsonl").open("x",encoding="utf-8") as f:
        for row in all_rows:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    base.write(OUT/"launch_failures.json",failed)
    print("Collected",len(all_rows),"real trials; preserved",len(failed),"pre-model launch failures")
