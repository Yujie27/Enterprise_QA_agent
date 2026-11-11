"""This experiment's manual layered adjudication. Not an automatic judge."""
import ast,difflib,json,subprocess
from collections import Counter
from statistics import mean
import agent_baseline as b

o=b.ROOT/'examples/evaluation/dg_targeted/20261111_v020'
rows=[json.loads(s) for s in (o/'observations.jsonl').read_text(encoding='utf-8').splitlines()]
notes={
'C11_r1_control':'首次D01/D04齐全，读双方后完整回答，无附加规则。',
'C11_r2_control':'事实与引用完整，释义用“费用发生之日起30日内”。单独标措辞风险待人工复核，不视为已明确编造当日/次日计算规则。',
'C11_r3_control':'事实与引用完整，仍补查附件清单，额外第五次被拒，状态incomplete；未伪称最后一次搜索已执行。',
'C11_r1_dg_targeted':'首次齐全后又搜索30/60/90日期限及差旅审批单，无新增；第五次read(D04)被拒。最终如实说明只依据D04检索片段，未声称已读全文。',
'C11_r2_dg_targeted':'首次已齐全，第二搜材料仍只得原两条，再读双方；答案正确保留范围未知，无细则补造。',
'C11_r3_dg_targeted':'首次齐全，读双方后仍查材料清单无新增；答案正确，不代表结束机制已可靠。',
'C01_r1_control':'双方可见并读取，主结论并列冲突追问正确，末句“同范围规则矛盾”把范围未知说成同范围，属于适用性判断扩张。',
'C01_r1_dg_targeted':'双方可见并读取，明确范围未提供、优先级未知，请求确认，不选期限；额外提议提供费用日期核截止日非已给计算规则，记非必要追问风险。',
'C13_r1_control':'双方可见并读取，仍建议按较严格15日提交。即使注明风险建议，也无制度依据，不通过。',
'C13_r1_dg_targeted':'双方可见并读取，明确范围未知，并列30/15日请求依据，没有先按短期限的建议。',
'R10_r1_control':'按实际范围回答研发差旅15日；搜索没有D03年假，未混答。',
'R10_r1_dg_targeted':'一次search按片段回答研发差旅15日；未命中D03年假。过程说明未与记录冲突，但本次噪声路径未触发。',
'C02_r1_control':'唯一D01有据回答30日，正常单证据回答。',
'C02_r1_dg_targeted':'仍有据答30日，不推断通用范围；但额外查费用发生后/差旅起算，合计4次工具，终止成本比对照2次更高。',
'E03_r1_control':'取得并读取D01，检索定义后说明工作日/自然日口径缺失，未给执行口径。',
'E03_r1_dg_targeted':'取得并读取D01，正确保留计算口径缺失；说明与实际工具一致。',
'F01_r1_control':'两次工具错误后停止，区分故障与制度不存在，无来源期限或时间补造。错误名称简写为simulated search failure不改变含义。',
'F01_r1_dg_targeted':'两次真实故障路径后停止，没有声称制度不存在或虚构错误时间。'}
unsupported={'C01_r1_control':['因同范围规则矛盾且无优先级'],'C13_r1_control':['费用发生后15日内提交（风险控制建议）']}
for r in rows:
    pending=r['run_id']=='C11_r2_control';bad=r['run_id'] in unsupported
    r['prompt_mode']=r['threshold']
    r['review']=dict(question_response_complete=True,citations_support_conclusions=True if r['case_id']!='F01' else None,
        unsupported_meaning=unsupported.get(r['run_id'],[]),process_errors=[],
        wording_risks=['原文“费用发生后30日内”，回答“费用发生之日起30日内”，完整回答和工具原文见本记录；待人工复核，不归为明确计算规则编造'] if pending else ['提供费用发生日期核截止日是非必要追问，未实际给出计算口径'] if r['run_id']=='C01_r1_dg_targeted' else [],
        business_verdict='pending_wording_review' if pending else 'fail' if bad else 'pass',reason=notes[r['run_id']])
    seen=set();first_full=None;after=[];no_new=0
    for s in r['steps']:
        keys=set(s['visible_keys'])
        if first_full is not None:after.append(s)
        if s['tool']=='search_docs' and s['type']=='tool_call' and not s['full_return'].get('error') and seen and not keys-seen:no_new+=1
        seen.update(keys)
        if r['required'] and set(r['required'])<=seen and first_full is None:first_full=s['step']
    r['coverage_complete_at_step']=first_full
    r['post_coverage_authorized_tools']=sum(s['type']=='tool_call' for s in after)
    r['no_new_searches']=no_new
    r['c11_post_sufficient_searches']=sum(s['type']=='tool_call' and s['tool']=='search_docs' for s in after) if r['case_id']=='C11' else None
    r['correct_terminal']=r['status'] in {'completed','insufficient_evidence','tool_error'}
    t=b.read(b.ROOT/r['trace'])
    assert t['experiment_config']==dict(retrieval_mode='dedup',demand_rewrite=False,match_threshold='one_overlap',dg_targeted=r['prompt_mode']=='dg_targeted')
    metadata=b.read((b.ROOT/r['trace']).parent.parent/'reply_metadata.json')
    assert all(x['finished_reason']=='completed' and not x['error'] for x in metadata)
    path=o/'per_run';path.mkdir(exist_ok=True);b.write(path/(r['run_id']+'.json'),r)
with (o/'results.jsonl').open('x',encoding='utf-8') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
metrics={}
for mode in ['control','dg_targeted']:
    rs=[r for r in rows if r['prompt_mode']==mode];positive=[r for r in rs if r['required']];c11=[r for r in rs if r['case_id']=='C11']
    metrics[mode]=dict(runs=len(rs),first_recall=mean(r['first_recall'] for r in positive),cumulative_recall=mean(r['cumulative_recall'] for r in positive),coverage_denominator=len(positive),confirmed_business_pass=sum(r['review']['business_verdict']=='pass' for r in rs),pending_wording=sum(r['review']['business_verdict']=='pending_wording_review' for r in rs),confirmed_business_fail=sum(r['review']['business_verdict']=='fail' for r in rs),correct_terminal_confirmed_pass=sum(r['correct_terminal'] and r['review']['business_verdict']=='pass' for r in rs),completed_confirmed_pass=sum(r['status']=='completed' and r['review']['business_verdict']=='pass' for r in rs),complete_responses=sum(r['review']['question_response_complete'] for r in rs),supported_citation_runs=sum(r['review']['citations_support_conclusions'] is True for r in rs),unsupported_runs=sum(bool(r['review']['unsupported_meaning']) for r in rs),process_error_runs=0,tools=sum(r['tool_calls'] for r in rs),budget_rejections=sum(r['budget_rejections'] for r in rs),no_new_searches=sum(r['no_new_searches'] for r in rs),statuses=dict(Counter(r['status'] for r in rs)),c11_tools=sum(r['tool_calls'] for r in c11),c11_post_coverage_searches=sum(r['c11_post_sufficient_searches'] for r in c11),c11_post_coverage_tools=sum(r['post_coverage_authorized_tools'] for r in c11))
b.write(o/'metrics.json',metrics)
sys_path=b.ROOT/'src/enterprise_qa_agent/agent.py'
module=ast.parse(sys_path.read_text(encoding='utf-8'));prompts={n.targets[0].id:ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'SYSTEM_PROMPT','DG_TARGETED_PROMPT'}}
(o/'control_prompt.txt').write_text(prompts['SYSTEM_PROMPT'],encoding='utf-8');(o/'experimental_prompt.txt').write_text(prompts['SYSTEM_PROMPT']+prompts['DG_TARGETED_PROMPT'],encoding='utf-8')
(o/'prompt_diff.patch').write_text(''.join(difflib.unified_diff(prompts['SYSTEM_PROMPT'].splitlines(True),(prompts['SYSTEM_PROMPT']+prompts['DG_TARGETED_PROMPT']).splitlines(True),fromfile='control_prompt',tofile='experimental_prompt')),encoding='utf-8')
lines=['# D/G定向实验：未知条件分类表达、有据回答与充分证据后结束','','本轮仅追加提示策略，不是完整C/D；主动冲突来源补查仍未实现。未修改历史报告。全部18次真实运行按原计划交替执行，两组各9次，独立会话、无业务重跑、无Mock、未执行0次。','','## 固定条件与工程边界','','两组dedup开启、one_overlap、demand-rewrite关闭，同一deepseek-flash配置，默认k=5和每轮4次工具不变；模型自主limit可为5/8/10。配置见config.json、trials/manifest.json；资料及必要证据见trials/plan.json。run字段threshold沿用运行器旧字段名，本轮仅表示control/dg_targeted提示组，物理门槛两组均one_overlap。','','源代码仅增加DG_TARGETED_PROMPT、默认关闭的recorder/CLI标志和Trace配置字段；检索、工具执行、评分、排序、词表、语料、gold未改变。实际[提示差异](prompt_diff.patch)、[原提示](control_prompt.txt)、[实验提示](experimental_prompt.txt)已封存。26项测试通过，0失败（0.430秒），含开关只改变提示而不改变工具schema与预算配置的测试。','','本轮没有程序语义保证、输出字符串删除、固定路径或额外模型裁判。公开decision_reason来自模型工具参数，完整返回与原始Trace保存；没有私有思维日志。先行冻结判据及模型配置保留在plan/manifest，人工逐条复核仅使用真实可见证据。','','## 分层定义与结果','','覆盖分母每组8次：排除F01预期故障，其他必要键沿用旧gold和E03入口D01；冲突要求双方，C11期限和票据两项都需可见。全部8次首搜与累计Recall均100%，不能据此自动通过业务。','','问题完整回应包括有据事实回答、合理冲突追问、口径缺失或故障说明；不意味着每题都有唯一事实答案。引用支持与新增断言分别评价，正确原文引用不能抵消附带无依据建议。F01未取得资料且未引文，因此引用分母8。','','“发生之日起”单列待人工复核：不自动算明确当日/次日规则错误，也不直接无条件确认通过。已确认通过、待复核、失败互斥；当前没有更改此前门槛Agent实验的严格判定。正确终止含completed、合理insufficient_evidence及预期tool_error，排除incomplete。','','|组|首搜/累计Recall|问题完整回应|引用支持|确认通过/待复核/失败|正确终止且确认通过|completed且确认通过|无依据含义运行|过程错误|工具/拒绝|状态|','|---|---|---|---|---|---|---|---|---|---|---|']
for mode,m in metrics.items():lines.append(f"|{mode}|{m['first_recall']:.0%}/{m['cumulative_recall']:.0%}（8）|{m['complete_responses']}/9|{m['supported_citation_runs']}/8|{m['confirmed_business_pass']}/{m['pending_wording']}/{m['confirmed_business_fail']}|{m['correct_terminal_confirmed_pass']}/9|{m['completed_confirmed_pass']}/9|{m['unsupported_runs']}|{m['process_error_runs']}|{m['tools']}/{m['budget_rejections']}|{m['statuses']}|")
lines+=['','对照C11_r2若人工接受该释义，则对照业务通过与正确终止且通过各增加1；若拒绝则判失败。本报告不把待复核包装成已验证收益。两组均0次明确当日/次日、工作日/自然日、故障发生时间编造。','','## 逐条判定及完整Trace','','|运行|状态/调用/拒绝|业务判定|说明|完整结果|Trace|','|---|---|---|---|---|---|']
for r in rows:
    path=str((b.ROOT/r['trace']).relative_to(o)).replace('\\','/')
    lines.append(f"|{r['run_id']}|{r['status']}/{r['tool_calls']}/{r['budget_rejections']}|{r['review']['business_verdict']}|{r['review']['reason']}|[记录](per_run/{r['run_id']}.json)|[Trace]({path})|")
lines+=['','## 1. 证据齐全后的追查有没有减少？','','没有。C11两组首搜均已有D01/D04。对照工具10次、充分后额外搜索1次；实验工具12次、充分后额外搜索4次；两组都出现一次第五次拒绝。实验C11_r1首次已经足够，仍搜索30/60/90日和差旅审批单，最终read(D04)被拒；r3读完两份后还搜材料清单。全文核验不是所有情况下都无效，但上述简单问题的额外搜索没有新增证据且超出了已问需求。','','C02单证据实验组仍能有据答30日，没有过度拒答；却用了4次工具，对照2次，额外检索差旅/起算，属于结束成本退化。C13实验3次相对对照4次有所减少，但不能抵消C11/C02的总体成本。本轮工具总数对照26、实验28，未证明提示能改善结束。冲突两组都读取双方，没有为了少工具跳过核验。','','## 2. 未知scope有没有被扩成已知范围？','','对照C01末句“同范围规则矛盾”与两份scope未提供不一致，严格失败。实验C01/C13都明确范围未知、请求适用及优先级依据，没有说都适用/同范围/通用或同层级。对照C13的“适用范围情况相同”随后明确均未提供，视为元数据缺失状态相同，不混同为已知实际范围；它失败的明确理由是附加15日执行建议。样本仅各一次，不能保证未来不会复发。','','## 3. 执行建议和过程断言有没有减少？','','对照C13附加按较严格15日提交的风险建议，实验未出现。对照/实验过程错误均0，不可宣称已证明过程断言减少。R10两组均没有D03年假候选，未混答年假；上一轮候选已见却称未检索的路径本轮未触发，因此不能证明该问题已修复。实验C11_r1明确D04只见检索片段、全文读取被拒，描述属实。','','对照C11_r2原文“费用报销应在费用发生后30日内提交申请。”、回答释义“在费用发生之日起30日内提交报销申请”；完整回答与全部原文见per_run/C11_r2_control.json。它可能只是自然释义，也可能被理解为指定起算日，故仅待人工复核。实验C01多提费用日期核截止日属非必要追问，尚未实际给出未定义口径，不算已编造计算规则。','','## 4. 正常/冲突/不足/故障是否退化？','','单证据C02答案与引用未退化，但工具成本增加；冲突C01/C13均取得双方并核验，实验无短期限建议且保留范围未知。E03两组都取得并读取D01，均保留日历口径缺失、未声称未见原文已核验；F01两组都真实触发2次同类错误，正确停止并区分工具故障与制度不存在，无时间补造。两组status均7 completed、1 incomplete、1 tool_error，insufficient_evidence均0；E03虽业务资料不足，CLI因有候选标completed，不能把该标签等同唯一答案已确定。','','## 复现与限制','','```powershell','.venv/Scripts/python.exe -B -m unittest discover -s tests -v','.venv/Scripts/python.exe -B scripts/dg_targeted.py prepare --output examples/evaluation/dg_targeted/replay01','.venv/Scripts/python.exe -B scripts/dg_targeted.py run --output examples/evaluation/dg_targeted/replay01','.venv/Scripts/python.exe -B scripts/collect_threshold_agent.py --output examples/evaluation/dg_targeted/replay01','# 对新结果独立人工复核；不要套用本次report_dg_targeted.py里的判定。','uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted "报销期限与所需材料是什么？"','```','','默认仍original门槛、dg-targeted关闭；实验开关仅用于明确选择。真实接口需网络权限和本地.env，命令不含密钥。输出目录拒绝覆盖已有会话。模型采样/seed沿用服务默认，小样本、每对先对照后实验存在顺序效应，不作显著性或因果保证；提示分类看似改善不证明程序语义分类能力。主动冲突来源补查仍未实现。没有更改历史gold、报告或结果，没有提交或推送Git。']
(o/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
before=b.read(o/'before.json');assert all(b.sha(b.ROOT/p)==h for p,h in before['history'].items())
assert b.sha(b.ROOT/'src/enterprise_qa_agent/knowledge.py')==before['source']['src/enterprise_qa_agent/knowledge.py']
b.check(o/'trials')
for p in (b.ROOT/'src').rglob('*.py'):
    target=o/'evaluated_source'/p.relative_to(b.ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(o/'worktree.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=b.ROOT))
b.write(o/'tests.json',dict(command='.venv/Scripts/python.exe -B -m unittest discover -s tests -v',tests=26,failures=0,errors=0,seconds=0.430))
b.write(o/'final_audit.json',dict(historical_files_verified=len(before['history']),real_runs=18,unexecuted=0,source_hashes={b.rel(p):b.sha(p) for p in (b.ROOT/'src').rglob('*.py')},default_threshold='original',dg_default=False,active_conflict_supplementation=False,git_staged=b.git('diff','--cached','--stat'),artifacts={str(p.relative_to(o)):b.sha(p) for p in o.rglob('*') if p.is_file()}))
print(json.dumps(metrics,ensure_ascii=False,indent=2))
