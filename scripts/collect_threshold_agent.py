"""Collect exact real outputs, without automatically judging business success."""
import json
from pathlib import Path
import agent_baseline as b
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
o=a.output.resolve();f=o/'trials'
b.check(f);plan=b.read(f/'plan.json');rows=[]
for item in plan['runs']:
    session=f/'sessions'/item['run_id'];traces=list((session/'traces').glob('*.json'))
    case=next(c for c in plan['cases'] if c['case_id']==item['case_id'])
    if not traces:
        rows.append(dict(**item,execution='not_executed',execution_record=b.read(session/'execution.json') if (session/'execution.json').exists() else None));continue
    t=b.read(traces[0]);returns=b.read(session/'tool_returns.json');slots=[e for e in t['events'] if e['type'] in {'tool_call','limit'}]
    assert len(returns)==len(slots)
    seen=set();first=None;at={};steps=[];req={e['doc_id']+'/'+e['section_id'] for e in case['necessary_evidence']}
    for event,ret in zip(slots,returns):
        payload=ret['payload_passed_to_original_tool_response'];hits=list(payload.get('results',[]));doc=payload.get('document')
        if doc:hits += [dict(doc_id=doc['doc_id'],**s) for s in doc['sections']]
        keys={h['doc_id']+'/'+h['section_id'] for h in hits}
        if first is None and event['tool']=='search_docs':first=keys
        for key in keys:at.setdefault(key,event['step'])
        seen.update(keys);steps.append(dict(**event,full_return=payload,visible_keys=sorted(keys)))
    rows.append(dict(**item,execution='attempted',messages=case['messages'],corpus=case['corpus'],corpus_sha256=case['corpus_sha256'],trace=b.rel(traces[0]),status=t['status'],answer=t['answer'],tool_calls=t['tool_calls'],steps=steps,required=sorted(req),missing=sorted(req-seen),first_recall=len(req&(first or set()))/len(req) if req else None,cumulative_recall=len(req&seen)/len(req) if req else None,acquired_at=at,budget_rejections=sum(e['type']=='limit' for e in slots),review=None))
with (o/'observations.jsonl').open('x',encoding='utf-8') as stream:
    for r in rows:stream.write(json.dumps(r,ensure_ascii=False)+'\n')
print('collected',len(rows))
