"""Alternating sequential real Agent trials; no business retries or model rewrites."""
import argparse,json,sys,subprocess,os
from pathlib import Path
import agent_baseline as b
p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id');a=p.parse_args();o=a.output.resolve()
if a.stage=='prepare':
    o.mkdir(parents=True,exist_ok=False)
    history={b.rel(p):b.sha(p) for p in (b.ROOT/'examples/evaluation').rglob('*') if p.is_file() and o not in p.parents}
    frozen={}
    for source in list((b.ROOT/'src').rglob('*.py'))+[b.ROOT/'pyproject.toml',b.ROOT/'uv.lock',b.ROOT/'.env.example']:
        target=o/'candidate'/source.relative_to(b.ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());frozen[b.rel(source)]=b.sha(source)
    (o/'candidate/worktree.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=b.ROOT))
    b.write(o/'candidate/freeze.json',dict(commit=b.git('rev-parse','HEAD'),branch=b.git('branch','--show-current'),worktree=b.git('status','--short'),hashes=frozen,history=history,model=b.config()))
    b.prepare(o/'trials')
    f=o/'trials'; plan=b.read(f/'plan.json')
    design={c['id']:c for c in b.read(b.BASELINE/'input/qa_boundary_test_design/cases.json')['cases']}
    gold={c['case_id']:c for c in b.read(b.BASELINE/'gold.json')['cases']}
    ids=['R01','C01','C02','R06','R02','M01','F01','F02','C05','C06','C09','C10','C12','C13','X06','X04','X05','C11']
    cases=[]
    for cid in ids:
        d=design[cid];corpus=b.BASELINE/'input/qa_boundary_test_design'/d['corpus']
        evidence=gold.get(cid,{}).get('necessary_evidence',[]) if cid!='E03' else [dict(doc_id='D01',section_id='D01-S1')]
        if cid=='M01':evidence=[dict(doc_id='D02',section_id='D02-S1')]
        cases.append(dict(case_id=cid,messages=d['messages'],corpus=b.rel(corpus),corpus_sha256=b.sha(corpus),necessary_evidence=evidence,simulate_failure='search_docs' if cid=='F01' else 'read_doc' if cid=='F02' else None,expected=d['expected']))
    runs=[]
    for cid in ids:runs.append(dict(run_id=cid+'_native',case_id=cid,repeat=1,batch='acceptance',threshold='dg_targeted'))
    runs.append(dict(run_id='C01_reverse',case_id='C01',repeat=1,batch='acceptance',threshold='dg_targeted',controlled_reverse=True))
    plan.update(cases=cases,runs=runs)
    (f/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    m=b.read(f/'manifest.json');m.update(plan_sha256=b.sha(f/'plan.json'),case_count=len(ids),session_count=len(runs),user_turn_count=20)
    (f/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    b.write(o/'config.json',dict(dedup=True,demand_rewrite=False,match_threshold='one_overlap',dg_targeted=True,budget=4,default_k=5,execution='independent sessions, M01 same session; reverse is explicitly controlled adapter',model=m['model_config']))
elif a.stage=='worker':
    sys.path.insert(0,str(b.ROOT/'src'))
    from enterprise_qa_agent import cli
    item=next(r for r in b.read(o/'trials/plan.json')['runs'] if r['run_id']==a.run_id)
    original=cli.main
    reverse_log=[]
    if item.get('controlled_reverse'):
        original_kb=cli.KnowledgeBase
        class ReverseKB(original_kb):
            def search(self,query,limit=5):
                hits=super().search(query,limit)
                reverse_log.append(dict(query=query,before=hits,after=list(reversed(hits))))
                return list(reversed(hits))
        cli.KnowledgeBase=ReverseKB
    def configured():
        sys.argv+=['--retrieval-mode','dedup','--match-threshold','one_overlap']
        if item['threshold']=='dg_targeted':sys.argv+=['--dg-targeted']
        original()
    cli.main=configured;b.worker(o/'trials',a.run_id)
    if item.get('controlled_reverse'):b.write(o/'trials/sessions'/a.run_id/'order_adapter.json',reverse_log)
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
