"""Explicit candidate demonstration entry. Invokes the real CLI, no preset answers."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'examples/evaluation/retrieval_baseline/20261110_raw_query_v020/input/qa_boundary_test_design'
SCENARIOS={'normal':'R01','conflict':'C01','single':'C02','outside':'R06','rewrite':'R02','multi':'M01','search-failure':'F01','read-failure':'F02','replace45':'X06'}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('scenario',choices=SCENARIOS);p.add_argument('--trace-dir',type=Path,default=ROOT/'examples/runs');a=p.parse_args()
case=next(c for c in json.loads((BASE/'cases.json').read_text(encoding='utf-8'))['cases'] if c['id']==SCENARIOS[a.scenario])
command=[sys.executable,'-m','enterprise_qa_agent.cli','--retrieval-mode','dedup','--match-threshold','one_overlap','--dg-targeted','--corpus',str(BASE/case['corpus']),'--trace-dir',str(a.trace_dir)]
if a.scenario in {'search-failure','read-failure'}:command+=['--simulate-failure','search_docs' if a.scenario=='search-failure' else 'read_doc']
if len(case['messages'])>1:
    command+=['--interactive']
    for message in case['messages'][1:]:command+=['--follow-up',message['content']]
command+=[case['messages'][0]['content']]
raise SystemExit(subprocess.call(command,cwd=ROOT))
