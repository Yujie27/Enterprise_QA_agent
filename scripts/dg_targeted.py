"""Alternating sequential real Agent trials; no business retries or model rewrites."""
import argparse,json,sys,subprocess,os
from pathlib import Path
import agent_baseline as b
p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id');a=p.parse_args();o=a.output.resolve()
if a.stage=='prepare':
    b.prepare(o/'trials')
    f=o/'trials'; plan=b.read(f/'plan.json')
    design={c['id']:c for c in b.read(b.BASELINE/'input/qa_boundary_test_design/cases.json')['cases']}
    gold={c['case_id']:c for c in b.read(b.BASELINE/'gold.json')['cases']}
    ids=['C11','C01','C13','R10','C02','E03','F01']
    cases=[]
    for cid in ids:
        d=design[cid];corpus=b.BASELINE/'input/qa_boundary_test_design'/d['corpus']
        evidence=gold.get(cid,{}).get('necessary_evidence',[]) if cid!='E03' else [dict(doc_id='D01',section_id='D01-S1')]
        cases.append(dict(case_id=cid,messages=d['messages'],corpus=b.rel(corpus),corpus_sha256=b.sha(corpus),necessary_evidence=evidence,simulate_failure='search_docs' if cid=='F01' else None,expected=d['expected']))
    runs=[]
    for cid,n in [('C11',1),('C11',2),('C11',3)]+[(c,1) for c in ids[1:]]:
        for mode in ['control','dg_targeted']:runs.append(dict(run_id=f'{cid}_r{n}_{mode}',case_id=cid,repeat=n,batch='alternating',threshold=mode))
    plan.update(cases=cases,runs=runs)
    (f/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    m=b.read(f/'manifest.json');m.update(plan_sha256=b.sha(f/'plan.json'),case_count=7,session_count=18,user_turn_count=18)
    (f/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    b.write(o/'config.json',dict(dedup=True,demand_rewrite=False,match_threshold='one_overlap',prompt_modes=['control','dg_targeted'],budget=4,default_k=5,execution='sequential control then treatment within each case/repeat',model=m['model_config']))
elif a.stage=='worker':
    sys.path.insert(0,str(b.ROOT/'src'))
    from enterprise_qa_agent import cli
    item=next(r for r in b.read(o/'trials/plan.json')['runs'] if r['run_id']==a.run_id)
    original=cli.main
    def configured():
        sys.argv+=['--retrieval-mode','dedup','--match-threshold','one_overlap']
        if item['threshold']=='dg_targeted':sys.argv+=['--dg-targeted']
        original()
    cli.main=configured;b.worker(o/'trials',a.run_id)
else:
    f=o/'trials';b.check(f);logs=f/'launcher';logs.mkdir(exist_ok=True)
    for r in b.read(f/'plan.json')['runs']:
        assert not (f/'sessions'/r['run_id']).exists()
        try:
            result=subprocess.run([sys.executable,'-B',__file__,'worker','--output',str(o),'--run-id',r['run_id']],cwd=b.ROOT,env=dict(os.environ,PYTHONIOENCODING='utf-8'),capture_output=True,timeout=900)
            code=result.returncode;stdout=result.stdout;stderr=result.stderr;timeout=False
        except subprocess.TimeoutExpired as exc:code=None;stdout=exc.stdout or b'';stderr=exc.stderr or b'';timeout=True
        for label,value in [('stdout',stdout),('stderr',stderr)]:
            (logs/(r['run_id']+'.'+label+'.txt')).write_text(b.redact(value.decode('utf-8',errors='replace')),encoding='utf-8')
        b.write(logs/(r['run_id']+'.json'),dict(returncode=code,timeout=timeout))
        traces=list((f/'sessions'/r['run_id']/'traces').glob('*.json'));t=b.read(traces[0]) if traces else {}
        print(r['run_id'],t.get('status','not_executed'),t.get('tool_calls'),flush=True)
    b.check(f)
