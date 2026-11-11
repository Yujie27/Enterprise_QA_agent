"""Manual relevance adjudication of the saved offline candidates; no reretrieval."""
import json
from collections import Counter
from pathlib import Path
from retrieval_baseline import ROOT,digest,write_json
out=ROOT/'examples/evaluation/threshold_diagnostic/20261111_v020'
manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
rows=[json.loads(s) for s in (out/'results.jsonl').read_text(encoding='utf-8').splitlines()]
gold=json.loads((ROOT/'examples/evaluation/retrieval_baseline/20261110_raw_query_v020/gold.json').read_text(encoding='utf-8'))
conflicts={c['case_id'] for c in gold['cases'] if c['business_answer_kind']=='conflict_report'}
def label(r,h):
    if h['relevance']!='unreviewed':return h['relevance']
    if r['group']=='C11_trace':return 'related_other_intent'
    if h['doc_id']=='D03' or h['doc_id'].startswith('N'):return 'irrelevant'
    return 'related_other_scope'
for r in rows:
    for m in r['modes'].values():
        for h in m['candidates']:h['relevance']=label(r,h)
    for h in r['added']:h['relevance']=label(r,h)
with (out/'reviewed_results.jsonl').open('x',encoding='utf-8') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
lines=['# 相关性复核与最终结论','','本文件补充原始summary的待复核项；不改变原gold或检索输出。人工复核实际条款：非差旅普通费用是范围对照；年假与预算申请噪声不支持报销期限；C11另一意图条款是同主题但不支持当前聚焦需求。R06是排除性边界，不能作为申请办法。','','|k|原→放宽冲突完整/9|原相关候选/总数→放宽|新增支持/相关但不足/无关|','|---|---|---|---|']
for k in [1,3,5,10]:
    rs=[r for r in rows if r['group']=='frozen' and r['k']==k and not r['excluded']]
    cs=[r for r in rs if r['id'] in conflicts]
    c=[sum(r['modes'][m]['complete'] for r in cs) for m in ['original','one_overlap']]
    counts=[]
    for m in ['original','one_overlap']:
        hs=[h for r in rs for h in r['modes'][m]['candidates']];counts.append(f"{sum(h['relevance']!='irrelevant' for h in hs)}/{len(hs)}")
    added=Counter(h['relevance'] for r in rs for h in r['added'])
    lines.append(f'|{k}|{c[0]}/9→{c[1]}/9|{counts[0]}→{counts[1]}|{dict(added)}|')
rs=[r for r in rows if r['group']=='C11_trace' and r['k']==5]
material=[r for r in rs if r['required']==[['D04','D04-S1']]]
lines+=['',f'23条真实C11搜索请求（重复保留）在k≥3必要目标完整由8/23→23/23；聚焦材料请求{len(material)}条，目标仅D04，完整由{sum(r["modes"]["original"]["complete"] for r in material)}/{len(material)}→{len(material)}/{len(material)}。k=1仍受排序截断，不能声称放宽必然解决。', '', '冻结27题×4k×2模式=216次；C11实际请求23×4×2=184次；开发4题×4×2=32次，总432次离线search，无真实模型。R05排除总体，DEV01未使用。', '', '诊断结论：本批失败查询的D04主要被至少2重叠的硬门槛阻断，放宽至1后可恢复；原冻结正例宏Recall在k≥3由98%→100%，未出现必要证据退化。但新增候选并非都支持：年假条款也进入报销查询，C11聚焦材料时期限条款被一并带入。相关性与支持性必须分开看。', '', '不建议仅据本轮改默认门槛。保留A＋去重为推荐配置；需要后续研究候选筛选与更广负例。两个真正无关开发问题使用设备资料，均没有候选；它们未触发同主题噪声，不能证明负例安全，冻结题已出现噪声代价。开发图书条件恢复、设备题无变化，单独报告，不混入冻结分母。', '', '复现命令见summary.md。threshold_diagnostic.py的两个隔离模式使用相同源码，唯一替换minimum_overlap表达式；业务源码完全未改。首次运行在最后审计写入遇到Windows默认GBK解码错误，所有432次检索与结果已保存；修正显式UTF-8后本脚本完成审计，没有重选或覆盖检索输出。']
(out/'final_summary.md').write_text('\n'.join(lines),encoding='utf-8')
assert all(digest(ROOT/p)==h for p,h in manifest['history_sha256'].items())
write_json(out/'audit.json',dict(historical_files_unchanged=len(manifest['history_sha256']),model_calls=0,src_unchanged=digest(ROOT/'src/enterprise_qa_agent/knowledge.py')==manifest['source_sha256'],offline_searches=432))
print('\n'.join(lines))
