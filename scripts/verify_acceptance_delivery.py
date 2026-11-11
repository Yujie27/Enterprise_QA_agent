"""Verify immutable candidate/history and intentional post-run documentation edits."""
import json,os,re
import agent_baseline as b
o=b.ROOT/'examples/evaluation/final_acceptance/20261111_v020';frozen=b.read(o/'candidate/freeze.json');manifest=b.read(o/'trials/manifest.json')
assert all(b.sha(b.ROOT/p)==h for p,h in frozen['hashes'].items())
assert all(b.sha(b.ROOT/p)==h for p,h in frozen['history'].items())
changed=[p for p,h in manifest['protected_file_sha256'].items() if b.sha(b.ROOT/p)!=h]
assert changed==['README.md'],changed
assert b.config()==manifest['model_config']
rows=[json.loads(s) for s in (o/'results.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(rows)==19
for r in rows:
    trace=b.read(b.ROOT/r['trace']);assert trace['experiment_config']==dict(retrieval_mode='dedup',demand_rewrite=False,match_threshold='one_overlap',dg_targeted=True)
    assert len([s for s in r['steps'] if s['type']=='tool_call'])==r['tool_calls']<=4
    returns=b.read((b.ROOT/r['trace']).parent.parent/'tool_returns.json')
    assert len(returns)==len(r['steps'])
    for step,ret in zip(r['steps'],returns):
        assert step['full_return']==ret['payload_passed_to_original_tool_response']==json.loads(ret['returned_tool_response']['content'][0]['text'])
    assert b.sha(b.ROOT/r['corpus'])==r['corpus_sha256']
    if r['case_id']=='M01':assert len(r['conversation'])==4
documents=[b.ROOT/'README.md',b.ROOT/'examples/README.md',b.ROOT/'examples/acceptance/README.md']+list((b.ROOT/'docs').glob('*.md'))+list(o.glob('*.md'))
links=0;missing=[]
for p in documents:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):continue
        # Existing prose may include optional Markdown title; current links do not.
        target=target.split('#')[0]
        if not (p.parent/target).exists():missing.append(dict(file=b.rel(p),target=target))
        links+=1
assert not missing,missing
secret=os.getenv('OPENAI_API_KEY','')
if len(secret)>8:
    assert not any(secret.encode() in p.read_bytes() for p in list(o.rglob('*'))+documents if p.is_file())
assert not b.git('diff','--cached','--stat')
b.write(o/'delivery_receipt.json',dict(candidate_source_unchanged=True,historical_files_unchanged=len(frozen['history']),real_runs=19,source_identity=b.read(o/'candidate/identity.json')['identity_sha256'],documentation_changes_after_runs=changed,links_checked=links,docs_sha256={b.rel(p):b.sha(p) for p in documents},artifacts_sha256={str(p.relative_to(o)):b.sha(p) for p in o.rglob('*') if p.is_file()},model_config_unchanged=True,git_status=b.git('status','--short'),git_staged='',no_commit_or_push=True,personal_time='待候选人补充'))
print('Verified immutable candidate/history, 19 exact tool-response sequences, multi-turn session,',links,'links, and post-run documentation changes')
