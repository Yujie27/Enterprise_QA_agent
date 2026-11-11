"""Run-specific manual review and report. Never apply these judgments to new trials."""
import json,subprocess
from pathlib import Path
from collections import Counter
from statistics import mean
import agent_baseline as b
root=b.ROOT/'examples/evaluation/threshold_agent/20261111_v020';o=root/'network_recovery'
rows=[json.loads(s) for s in (o/'observations.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(rows)==20 and all(r['execution']=='attempted' for r in rows)
notes={
'C11_r1_original':'第二步搜索取得D04，读双方后答30日和合规票据，无附加细则。',
'C11_r2_original':'后续搜索恢复D04，读双方，完整有据回答；未将示例材料列为必交清单。',
'C11_r3_original':'未取得D04，30日期限有据、材料缺口如实保留；目标不完整。',
'C11_r1_one_overlap':'首次已见D01/D04，读双方，完整答30日与合规票据，范围/材料细则未知。',
'C11_r2_one_overlap':'首次两证据齐全，读取后继续追查细则，第五次被拒；最终业务有据，但执行incomplete。',
'C11_r3_one_overlap':'首次两证据齐全，答案引用正确，但改述为“费用发生之日起30日内”，将未定义的起算日具体化；严格依据约束失败，未见次日起算。',
'R02_r1_original':'按D02研发差旅15日回答，正确排除非差旅D01，无年假候选。',
'R02_r1_one_overlap':'实际看到D03年假，未读取、未引用、未混入答案；仅一次search据D02回答，主答案有据。',
'R10_r1_original':'未见年假候选，read(D02)后答研发差旅15日，符合不要查年假的要求。',
'R10_r1_one_overlap':'第二次search实际有D03年假，未读或混入期限答案，但说“年假相关内容未纳入检索和回答”，前半句与记录相反；严格过程依据不通过。',
'C01_r1_original':'双方可见且核原文、请求依据，未选15日；但开头断言“两份都适用且都现行有效”，scope实际未提供，适用性断言无依据。',
'C01_r1_one_overlap':'双方可见、读取后列冲突并请求适用/优先级依据，没有先按15日建议。',
'C02_r1_original':'唯一D01可见并读取，按费用发生后30日限定原文范围回答，没有过度拒答。',
'C02_r1_one_overlap':'唯一D01可见并读取，正确给30日、元数据和原文，无额外执行口径。',
'C13_r1_original':'首次双方可见，read双方后并列30/15日请求依据，未按副本数量或日期选择。',
'C13_r1_one_overlap':'双方可见且read，主结论正确并追问，但末句断言“相同范围内直接矛盾”，实际scope未提供；与先前严格范围断言判据一致记失败。',
'R06_r1_original':'读到明确排除补贴的边界条款，后续搜索无结果，未把普通费用30日当补贴期限。',
'R06_r1_one_overlap':'检索和读取排除性边界，保留入口材料期限缺口，没有声称制度不存在。',
'E03_r1_original':'连续空返回，无D01，明确未引用任何条款，没有声称已核验原文；安全资料不足终止。',
'E03_r1_one_overlap':'首搜取得D01并实际读取，保留工作日/自然日口径未知，无无依据执行建议。'}
unsupported={'C11_r3_one_overlap':'费用发生之日起','R10_r1_one_overlap':'年假相关内容未纳入检索和回答','C01_r1_original':'两份都适用且都现行有效','C13_r1_one_overlap':'相同范围内直接矛盾'}
metrics={}
for r in rows:
    failed=r['run_id'] in unsupported or r['run_id']=='C11_r3_original'
    r['review']=dict(strict_business_pass=not failed,reason=notes[r['run_id']],unsupported_assertions=[unsupported[r['run_id']]] if r['run_id'] in unsupported else [],wrong_source_citations=[],review_method='助手逐条核验实际工具返回和回答；非模型自动裁判，建议候选人复审')
    r['correct_terminal_and_business_pass']=not failed and r['status'] in {'completed','insufficient_evidence','tool_error'}
    r['noise_steps']=[s['step'] for s in r['steps'] if any(h['doc_id']=='D03' for h in s['full_return'].get('results',[]))]
    r['noise_reads']=[s['step'] for s in r['steps'] if s['tool']=='read_doc' and s['arguments'].get('doc_id')=='D03']
    t=b.read(b.ROOT/r['trace']);assert t['experiment_config']==dict(retrieval_mode='dedup',demand_rewrite=False,match_threshold=r['threshold'])
for mode in ['original','one_overlap']:
    rs=[r for r in rows if r['threshold']==mode];positive=[r for r in rs if r['required']]
    metrics[mode]=dict(runs=len(rs),first_recall=mean(r['first_recall'] for r in positive),cumulative_recall=mean(r['cumulative_recall'] for r in positive),evidence_denominator=len(positive),first_complete=sum(r['first_recall']==1 for r in positive),cumulative_complete=sum(r['cumulative_recall']==1 for r in positive),business_pass=sum(r['review']['strict_business_pass'] for r in rs),correct_terminal_and_business_pass=sum(r['correct_terminal_and_business_pass'] for r in rs),completed_and_business_pass=sum(r['review']['strict_business_pass'] and r['status']=='completed' for r in rs),tools=sum(r['tool_calls'] for r in rs),budget_rejections=sum(r['budget_rejections'] for r in rs),unsupported_runs=sum(bool(r['review']['unsupported_assertions']) for r in rs),wrong_source_citations=0,statuses=dict(Counter(r['status'] for r in rs)))
b.write(o/'metrics.json',metrics)
with (o/'results.jsonl').open('x',encoding='utf-8') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
lines=['# 去重开启：原门槛与一个重合词项的真实Agent对照','','20次真实运行已完成，两组各10次，无Mock、无业务失败重跑、无挑选。C11首搜覆盖改善，但不能据此采用新默认；严格业务结果受附带断言和结束行为限制。','','## 固定条件与工程验证','','commit、初始工作区/历史哈希见../before.json；已测源文件哈希、模型及语料哈希见trials/manifest.json和plan.json。deepseek-flash原配置，demand-rewrite两组均关闭，去重开启，默认k=5、每轮4次工具、评分/排序/提示词/同义词/资料均未改。仅新增KnowledgeBase.match_threshold和CLI --match-threshold，默认original。每题/重复先对照后实验，单进程串行，独立会话，实际顺序与时间在plan及execution记录可核查。模型自主limit仍可变化。','','已有23项及新增2项共25测试通过，0失败，unittest报告0.365秒；新增测试逐一复核432条离线诊断输出与真实开关实现相同，验证空查询/零重合仍为空。','','初次沙箱启动遭WinError10013，停止时没有模型回复或Trace，记录原样保留于../trials。获准沙箱外联网后，在本network_recovery目录按原计划完整执行20次；不是业务重试。模型SDK仍沿用默认网络重试策略。prepare控制台打印prepared18是旧通用模板提示，冻结plan与manifest已明确20，实际记录也是20。','','## 指标','','Recall按原始doc_id/section_id必要证据，R06无可答申请办法，排除覆盖分母；E03沿用原Agent计划D01入口，故每组9个覆盖观察。首搜是模型自主首个查询，不是原始问题直接检索。累计仅计实际工具返回，不从全库补证据。','','严格业务通过要求目标完整、引用支持及无无依据制度/过程断言；安全部分回答不算完整。正确终止包括completed和有据说明资料不足的insufficient_evidence，预期tool_error也可计，但本次0；incomplete始终排除。另列completed且通过，避免用completed替代业务正确。','','|配置|首搜Recall/完整|累计Recall/完整|严格业务|正确终止且通过|completed且通过|工具数|预算拒绝|无依据断言运行|状态|','|---|---|---|---|---|---|---|---|---|---|']
for mode,m in metrics.items():lines.append(f"|{mode}|{m['first_recall']:.2%}；{m['first_complete']}/9|{m['cumulative_recall']:.2%}；{m['cumulative_complete']}/9|{m['business_pass']}/10|{m['correct_terminal_and_business_pass']}/10|{m['completed_and_business_pass']}/10|{m['tools']}|{m['budget_rejections']}|{m['unsupported_runs']}|{m['statuses']}|")
lines+=['','两组错误来源ID引用均0；四条附带断言见逐条表，不能把主结论正确当严格通过。范围相同/都适用与scope未提供不同；C11“之日起”也未由原文“发生后”确定，是严格口径的措辞风险。若评审将起算改述视为可接受，实验组业务和正确终止分别增加1，原始文本保留供复审，不反改主判定。','','## 逐条结果与Trace','','|运行|状态/工具/拒绝|证据D01/D04首次step（如适用）|严格业务|核验说明|Trace|','|---|---|---|---|---|---|']
for r in rows:
    path=Path(r['trace']).relative_to(o.relative_to(b.ROOT)).as_posix();at=r['acquired_at'];arrival=f"{at.get('D01/D01-S1','未见')}/{at.get('D04/D04-S1','未见')}" if r['case_id']=='C11' else '见完整结果'
    lines.append(f"|{r['run_id']}|{r['status']}/{r['tool_calls']}/{r['budget_rejections']}|{arrival}|{r['review']['strict_business_pass']}|{r['review']['reason']}|[Trace]({path})|")
lines+=['','## 噪声与结束成本','','R02原组候选无年假，实验组首搜D02/D01/D03，未read(D03)或引用年假，一次工具有据回答；调用数3→1。R10原组无年假，实验组第二次搜索D01/D02/D03，未读取年假、未把年假混成业务规则，但最终“未纳入检索”与记录矛盾；调用数2→3。两题合计5→4，不能据此说噪声增加净工具数：模型查询和路径也不同；R10额外搜索并未新增必要证据。观察到的实际代价是候选污染及过程说明不实，不是年假期限混答。','','C11原组首搜三次均只有D01，后续两次自主改写恢复D04；实验组首搜三次均同时D01+D04，主事实30日/合规票据都答出。原组严格2/3、正确终止2/3；实验组严格2/3（第三次起算改述失败）、正确终止1/3（第二次第五次请求被拒）。没有编造次日起算或将发票/审批单等列为必需材料；“发生之日起”作为未定义起算扩张单列。证据齐全仍追加材料细则搜索，故门槛不解决结束问题。','','C01/C13均首次看到冲突双方并读取原文，没有先按15日建议。原组C01擅称都适用、实验C13擅称同范围，属于回答依据风险，并非召回失败。C02两组唯一D01正常有据回答。R06正确将排除性条款当边界而非补贴办法；E03原组无原文安全拒答，实验组真实取得并读取D01后说明日历口径未知，两组均未假称核验未见原文。','','## 结论与限制','','放宽门槛改善了本批C11证据进入上下文的稳定性（首搜0/3→3/3，累计2/3→3/3），但没有改善严格且正常结束的端到端结果；不能宣布优化成功。噪声没有导致错误引用年假条款，却在R10产生不实过程断言，且原有无依据范围判断及过度追查仍在。当前证据不足以接受默认切换，建议后续独立验证候选筛选；本轮未实施任何筛选、重排、scope加权、冲突补查或回答校验。默认仍original。','','样本仅8种场景，只有C11三次，固定对照先执行存在顺序效应；模型服务默认采样/别名权重未知，调用差异不能全归因门槛。人工严格判据含可复核的措辞判断，不估计统计显著性。保留全部实际返回及公开理由，无私有思维日志。','','## 复现','','```powershell', '.venv/Scripts/python.exe -B -m unittest discover -s tests -v', '.venv/Scripts/python.exe -B scripts/threshold_agent.py prepare --output examples/evaluation/threshold_agent/replay01', '.venv/Scripts/python.exe -B scripts/threshold_agent.py run --output examples/evaluation/threshold_agent/replay01', '.venv/Scripts/python.exe -B scripts/collect_threshold_agent.py --output examples/evaluation/threshold_agent/replay01', '# 对新observations/Trace独立人工核验；不要套用本次report脚本内的判定。', '# 单次真实实验开关；不传时默认为original：', 'uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap "报销期限多久？"', '```', '', '完整结果见results.jsonl，全部工具原始对象见trials/sessions/*/tool_returns.json。本报告只复核本次输出；新目录拒绝覆盖旧session。']
(o/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
before=b.read(root/'before.json');assert all(b.sha(b.ROOT/p)==h for p,h in before['history'].items())
b.check(o/'trials')
for p in (b.ROOT/'src').rglob('*.py'):
    target=root/'evaluated_source'/p.relative_to(b.ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(root/'changes.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=b.ROOT))
b.write(root/'final_audit.json',dict(historical_files_unchanged=len(before['history']),real_runs=20,unexecuted_planned_runs=0,tests_passed=25,default_threshold='original',git_staged=b.git('diff','--cached','--stat'),source_hashes={b.rel(p):b.sha(p) for p in (b.ROOT/'src').rglob('*.py')},artifacts={b.rel(p):b.sha(p) for p in root.rglob('*') if p.is_file()}))
print(json.dumps(metrics,ensure_ascii=False,indent=2))
