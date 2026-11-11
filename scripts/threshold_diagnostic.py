"""Offline single-factor threshold diagnosis. Never imports model or changes src."""
import argparse, json, types, sys
from pathlib import Path
from time import perf_counter
from statistics import mean
from retrieval_baseline import digest, snapshot, write_json

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'examples/evaluation/retrieval_baseline/20261110_raw_query_v020'
B=ROOT/'examples/evaluation/demand_rewrite/20261110_v020'
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True)
a=p.parse_args(); out=a.output; out.mkdir(parents=True,exist_ok=False)
history={str(f.relative_to(ROOT)):digest(f) for f in (ROOT/'examples/evaluation').rglob('*') if f.is_file() and out.resolve() not in f.resolve().parents}
source=(ROOT/'src/enterprise_qa_agent/knowledge.py').read_text(encoding='utf-8')
needle='minimum_overlap = 1 if len(query_terms) <= 2 else 2'
assert source.count(needle)==1
write_json(out/'manifest.json',dict(version=snapshot(),history_sha256=history,source_sha256=digest(ROOT/'src/enterprise_qa_agent/knowledge.py'),gold_sha256=digest(BASE/'gold.json'),dedup=True,thresholds=['original','one_overlap'],ks=[1,3,5,10],model_calls=0,recommended_runtime='A＋去重; demand rewrite optional/off'))
gold=json.loads((BASE/'gold.json').read_text(encoding='utf-8'))
cases=[]
for c in gold['cases']:
    cases.append(dict(group='frozen',id=c['case_id'],query=c['original_query'],corpus=c['corpus'],required=[(e['doc_id'],e['section_id']) for e in c['necessary_evidence']],excluded=c['case_id']=='R05'))
for line in (B/'observations.jsonl').read_text(encoding='utf-8').splitlines():
    r=json.loads(line)
    if r['case_id']!='C11':continue
    for s in r['steps']:
        if s['tool']!='search_docs' or s['type']!='tool_call':continue
        q=s['arguments']['query']; material=not any(t in q for t in ['期限','时限'])
        cases.append(dict(group='C11_trace',id=f"{r['config']}/{r['run_id']}/step{s['step']}",query=q,corpus=r['corpus'],required=[('D04','D04-S1')] if material else [('D01','D01-S1')]+([('D04','D04-S1')] if any(t in q for t in ['材料','资料']) else []),excluded=False,trace=r['trace'],target_basis='聚焦材料仅D04；期限仅D01；同时询问两项则D01+D04；按实际查询文字事前固定'))
for identifier,q,required in [('DEV02','图书借阅需要满足什么条件，如何办理？',[('DEV02-1','DEV02-1-S1'),('DEV02-2','DEV02-2-S1')]),('DEV03','设备维修申请的时限和需要的资料是什么？',[('DEV03-1','DEV03-1-S1'),('DEV03-2','DEV03-2-S1')]),('UNRELATED1','火星天气预报',[]),('UNRELATED2','报销主题的火星天气预报',[])]:
    corpus=B/(('DEV03' if identifier.startswith('UNRELATED') else identifier)+'.json')
    cases.append(dict(group='development',id=identifier,query=q,corpus=str(corpus.relative_to(ROOT)),required=required,excluded=False))
write_json(out/'annotations.json',dict(cases=cases,relevance_policy='必要键为直接支持；经copied_from且文本/范围/版本/日期完全一致为等价支持；R06命中排除性说明为相关边界、不支持申请办法；范围对照条款为相关但不足；其他未标条款保守记待复核，不武断当无关。开发无关题全部候选无关。DEV01排除。'))
modules={}
for mode in ['original','one_overlap']:
    m=types.ModuleType('diagnostic_'+mode);m.__file__=str(ROOT/'src/enterprise_qa_agent/knowledge.py')
    exec(compile(source if mode=='original' else source.replace(needle,'minimum_overlap = 1'),m.__file__,'exec'),m.__dict__);modules[mode]=m
rows=[]
for c in cases:
    docs=json.loads((ROOT/c['corpus']).read_text(encoding='utf-8'))
    required=set(map(tuple,c['required']))
    for k in [1,3,5,10]:
        pair={}
        for mode,m in modules.items():
            start=perf_counter(); hits=m.KnowledgeBase(ROOT/c['corpus'],deduplicate=True).search(c['query'],k); elapsed=(perf_counter()-start)*1000
            for rank,h in enumerate(hits,1):
                key=(h['doc_id'],h['section_id']); equivalent=False
                d=next(d for d in docs if d['doc_id']==h['doc_id'])
                for original in docs:
                    if d.get('copied_from')==original['doc_id'] and any((original['doc_id'],s['section_id']) in required and s['text']==h['text'] for s in original['sections']) and all(d.get(t)==original.get(t) for t in ['scope','version','effective_from']):equivalent=True
                label='direct_support' if key in required else 'equivalent_support' if equivalent else 'irrelevant' if c['id'].startswith('UNRELATED') else 'boundary_related' if c['id']=='R06' else 'related_other_scope' if c['id']=='R07' else 'unreviewed'
                h.update(rank=rank,relevance=label,supports_requested_answer=label in ['direct_support','equivalent_support'])
            found={(h['doc_id'],h['section_id']) for h in hits}
            pair[mode]=dict(candidates=hits,elapsed_ms=elapsed,recall=len(required&found)/len(required) if required else None,complete=required<=found if required else None)
        old={(h['doc_id'],h['section_id']) for h in pair['original']['candidates']}
        rows.append(dict(**c,k=k,corpus_sha256=digest(ROOT/c['corpus']),modes=pair,added=[h for h in pair['one_overlap']['candidates'] if (h['doc_id'],h['section_id']) not in old],regression=bool(required and pair['one_overlap']['recall']<pair['original']['recall'])))
with (out/'results.jsonl').open('x',encoding='utf-8') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
lines=['# 检索匹配门槛诊断实验','','固定去重与来源呈现，仅在隔离加载的knowledge.py副本中把minimum_overlap改为1；原源码及默认行为未改。非空查询仍须有重合，评分排序及Top-k完全沿用。没有模型调用。','', '推荐运行仍为 `uv run --locked enterprise-qa --retrieval-mode dedup`；按需改写需显式添加`--demand-rewrite`。','','|组|k|原Recall→放宽|完整覆盖原→放宽|新增候选标签统计|退化|','|---|---|---|---|---|---|']
from collections import Counter
for group in ['frozen','C11_trace','development']:
    for k in [1,3,5,10]:
        rs=[r for r in rows if r['group']==group and r['k']==k and not r['excluded']];positive=[r for r in rs if r['required']]
        recalls=[mean(r['modes'][m]['recall'] for r in positive) for m in modules]
        counts=[sum(r['modes'][m]['complete'] for r in positive) for m in modules]
        labels=Counter(h['relevance'] for r in rs for h in r['added'])
        lines.append(f'|{group}|{k}|{recalls[0]:.2%}→{recalls[1]:.2%}|{counts[0]}/{len(positive)}→{counts[1]}/{len(positive)}|{dict(labels)}|{sum(r["regression"] for r in rs)}|')
lines+=['','必要证据按原始doc/section严格计算，R05探索性排除，R06不进入Recall分母；Trace按实际调用次数加权，重复查询保留。DEV01不用于比较。完整候选、分数、原文、元数据和新增候选见results.jsonl。','','相关条款比例必须报告上下界：direct/equivalent/boundary/other_scope视为相关，unreviewed不能直接算无关；下界=已标相关/候选总数，上界=(已标相关+待复核)/候选总数。边界相关不等于可答。']
for mode in modules:
    selected=[r for r in rows if r['group']=='frozen' and r['k']==5 and not r['excluded']]
    labels=Counter(h['relevance'] for r in selected for h in r['modes'][mode]['candidates']);total=sum(labels.values());known=total-labels['unreviewed']-labels['irrelevant']
    conflicts=[r for r in selected if r['id'] in ['C01','C03','C05','C09','C10','C12','C13','C14','C02'] and len(r['required'])>1]
    lines +=[f'\n{mode}冻结k=5候选标签：{dict(labels)}，相关比例区间{known}/{total}—{known+labels["unreviewed"]}/{total}。冲突子集完整：{sum(r["modes"][mode]["complete"] for r in conflicts)}/{len(conflicts)}（以列出的多证据冲突子集为准，非完整9题指标）。']
lines+=['','结论：请结合逐条D04变化判断硬门槛作用；放宽可允许原先只有一个重叠词的材料候选进入，但不能保证语义支持或解决未知范围。未完成相关性人工复核的候选明确保留不确定性，本轮不能仅凭召回提升推荐替换默认；需进一步研究候选筛选。未增加BM25、向量、重排或回答校验。','','复现：`.venv/Scripts/python.exe -B scripts/threshold_diagnostic.py --output examples/evaluation/threshold_diagnostic/replay_01`。独立目录排他创建。']
(out/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
assert all(digest(ROOT/f)==h for f,h in history.items())
write_json(out/'audit.json',dict(historical_files_unchanged=len(history),model_calls=0,src_unchanged=digest(ROOT/'src/enterprise_qa_agent/knowledge.py')==json.loads((out/'manifest.json').read_text(encoding='utf-8'))['source_sha256']))
print(out);print('\n'.join(lines[6:21]))
