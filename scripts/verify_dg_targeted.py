"""Final read-only verification and exact source diff against sealed prior run."""
import ast,difflib,json,os,re
import agent_baseline as b
o=b.ROOT/'examples/evaluation/dg_targeted/20261111_v020'
old=b.ROOT/'examples/evaluation/threshold_agent/20261111_v020/evaluated_source'
before=b.read(o/'before.json');diff=[]
for path,sha in before['source'].items():
    prior=old/path;current=b.ROOT/path
    assert b.sha(prior)==sha
    diff+=list(difflib.unified_diff(prior.read_text(encoding='utf-8').splitlines(True),current.read_text(encoding='utf-8').splitlines(True),fromfile='before/'+path,tofile='dg/'+path))
(o/'dg_changes.patch').write_text(''.join(diff),encoding='utf-8')
def functions(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(path.read_text(encoding='utf-8'))) if isinstance(n,ast.FunctionDef) and n.name in {'search_docs','read_doc','search_tool','read_tool'}}
assert functions(old/'src/enterprise_qa_agent/agent.py')==functions(b.ROOT/'src/enterprise_qa_agent/agent.py')
assert b.read(o/'config.json')['model']==b.read(b.ROOT/'examples/evaluation/threshold_agent/20261111_v020/network_recovery/config.json')['model']
rows=[json.loads(s) for s in (o/'results.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(rows)==18 and len({r['run_id'] for r in rows})==18
for row in rows:
    assert b.read(o/'per_run'/(row['run_id']+'.json'))==row
    assert b.sha(b.ROOT/row['corpus'])==row['corpus_sha256']
    assert len([s for s in row['steps'] if s['type']=='tool_call'])==row['tool_calls']<=4
    for s in row['steps']:
        payload=s['full_return']
        assert not payload.get('retrieval_statistics') # demand rewrite truly off
    trace=b.ROOT/row['trace'];assert trace.exists()
for target in re.findall(r'\]\(([^)]+)\)',(o/'summary.md').read_text(encoding='utf-8')):
    assert (o/target).exists(),target
assert all(b.sha(b.ROOT/p)==sha for p,sha in before['history'].items())
b.check(o/'trials')
secret=os.getenv('OPENAI_API_KEY','')
if len(secret)>8:assert not any(secret.encode() in p.read_bytes() for p in o.rglob('*') if p.is_file())
b.write(o/'final_validation.json',dict(real_runs=18,history_unchanged=len(before['history']),tool_implementations_equal=True,models_equal=True,source_diff='dg_changes.patch',default_threshold='original',artifacts_sha256={str(p.relative_to(o)):b.sha(p) for p in o.rglob('*') if p.is_file()},git_staged=b.git('diff','--cached','--stat')))
print('Verified 18 actual traces, identical tools/model, historical hashes, links and source diff')
