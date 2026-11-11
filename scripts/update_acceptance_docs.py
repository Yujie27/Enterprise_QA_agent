"""Delivery documentation only, after candidate runs and source verification."""
from pathlib import Path
import json,os
import agent_baseline as b
root=b.ROOT;o=root/'examples/evaluation/final_acceptance/20261111_v020'
rows=[json.loads(s) for s in (o/'results.jsonl').read_text(encoding='utf-8').splitlines()];lookup={r['run_id']:r for r in rows}
report='examples/evaluation/final_acceptance/20261111_v020/summary.md'
intro='''
## 最终候选评审入口（2026-11-11）

当前候选验收有保留：[验收报告](examples/evaluation/final_acceptance/20261111_v020/summary.md)、[逐条Trace索引](examples/acceptance/README.md)、[候选源码与依赖封存](examples/evaluation/final_acceptance/20261111_v020/candidate/identity.json)。18次原生真实运行17次严格业务通过；另1次受控返回顺序变体存在附加“同层级”断言。不能写成全部无缺陷达标或泛化准确率。

**业务默认没有切换**：dedup开启、original门槛、DG提示策略关闭、demand-rewrite关闭。**本次提交演示候选**显式启用dedup＋one_overlap＋dg-targeted，保持demand-rewrite关闭，每轮4次工具。

```powershell
uv sync --locked
# 首次配置本地.env后，直接演示真实候选；不需要切换源码
uv run --locked python scripts/submission_demo.py normal
uv run --locked python scripts/submission_demo.py conflict
uv run --locked python scripts/submission_demo.py single
uv run --locked python scripts/submission_demo.py replace45
uv run --locked python scripts/submission_demo.py outside
uv run --locked python scripts/submission_demo.py multi
uv run --locked python scripts/submission_demo.py search-failure
uv run --locked python scripts/submission_demo.py read-failure
# 原CLI也可以显式选择候选（默认资料含部门差异）
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted "研发部门差旅报销期限？"
```

演示入口仅选择固定合成输入和候选开关，真实模型自主决定工具路径，不预设答案。模型使用本地`.env`，本批为`deepseek-flash`、OpenAI兼容端点`https://api.deepseek.com/v1`、非流式、`parallel_tool_calls=False`；temperature/top_p/seed未显式设置。不可将密钥写进命令、文档或pyproject.toml。模型可能产生与已存记录不同的结果。

AgentScope 2.0.11负责模型与工具schema接入、ReAct循环、会话消息和权限；本项目负责检索、来源折叠、门槛实验、工具预算和Trace。Mock仅是预设流程检查，不证明模型动态决策。当前没有程序语义/引用断言保证。

已知限制：按需改写尚未证明稳定收益；D/G仅为提示策略；主动关联冲突来源补查尚未实现；简单问题仍可能追查触顶。C06额外逾期判断和顺序变体的“同层级”断言原样保留，未在验收中修复。26项自动测试通过；代码、评测和本轮文档均由AI辅助，候选人亲自完成范围与实际投入用时待本人核实补充。

以下为原有环境说明及历史演示入口；当前候选以本节显式配置为准，实验历史见`examples/evaluation/`，不与提交演示混称。

'''
p=root/'README.md';text=p.read_text(encoding='utf-8');head,tail=text.split('\n',1);p.write_text(head+'\n'+intro+tail,encoding='utf-8')
folder=root/'examples/acceptance';folder.mkdir(exist_ok=True)
lines=['# 最终候选：评审Trace索引','','这些是已保存的真实结果，不是预设决策日志。提交演示用scripts/submission_demo.py；完整实验和失败原样在../evaluation，不重新挑选运行。','','候选配置dedup＋one_overlap＋dg-targeted，demand-rewrite关闭，每轮4次工具；业务CLI默认未切换。','','|评审项目|记录与状态|完整结果|原始Trace|','|---|---|---|---|']
names=[('正常回答','R01_native'),('冲突核验并追问','C01_native'),('同题只留D01','C02_native'),('资料外问题','R06_native'),('相似表达','R02_native'),('同会话上下文','M01_native'),('搜索故障','F01_native'),('读取故障已触发','F02_native'),('明确替代及附加逾期判断失败','C06_native'),('同ID换45日','X06_native'),('编号改变','X05_native'),('返回顺序反转及层级断言失败','C01_reverse')]
for title,key in names:
    r=lookup[key];result=os.path.relpath(o/'per_run'/(key+'.json'),folder).replace('\\','/');trace=os.path.relpath(root/r['trace'],folder).replace('\\','/')
    lines.append(f"|{title}|{r['status']}，业务{r['review']['business_pass']}|[完整结果]({result})|[Trace]({trace})|")
budget=b.read(o/'supplemental_budget.json');trace=os.path.relpath(root/budget['trace'],folder).replace('\\','/')
lines += [f'|4次工具上限、明确未完成|同源码候选既有记录，incomplete；不计本轮新增分母|[来源与哈希核对](../evaluation/final_acceptance/20261111_v020/supplemental_budget.json)|[Trace]({trace})|','', '[完整报告](../evaluation/final_acceptance/20261111_v020/summary.md)包含所有19次结果、分类、失败、变换是否触发、复现命令和最小下一步建议。X04文件顺序被排序抵消，不能作为位置鲁棒性成功；受控reverse实际反转并出现附带错误，完整保留。','', '当前候选源码哈希标识见[identity](../evaluation/final_acceptance/20261111_v020/candidate/identity.json)，不是只靠旧commit。实际总用时待候选人补充，未将运行耗时冒充个人投入。']
(folder/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def append(path,content):
    with (root/path).open('a',encoding='utf-8') as f:f.write('\n\n'+content+'\n')
append('examples/README.md','## 2026-11-11 最终候选验收\n\n[当前候选评审索引](acceptance/README.md)区分正常、冲突、故障、替换及关键失败。旧记录不改；预算拒绝复用同源码候选既有真实记录，明确单列。')
append('docs/03-evaluation.md','''## 2026-11-11 最终候选（与上文历史结果分开）

[完整报告](../examples/evaluation/final_acceptance/20261111_v020/summary.md)与[Trace索引](../examples/acceptance/README.md)。26项工程测试通过（实际日志已保存）；18次原生真实验收17次业务通过，另1次独立受控返回顺序变体失败，总19次全部保留。未执行0次，原生16 completed和2 tool_error，受控1 completed；completed并不等同业务正确。

C01并列30/15日并读取双方追问；C02同一问题只留D01后答30；R01/X06同ID实际原文30→45、答案随之变化。M01同会话上下文正确；F01搜索与F02读取故障均实际触发。X04文件顺序变换被排序抵消，标未触发；隔离reverse适配器真实改变候选返回顺序，却补造“同层级”，不能宣称鲁棒性已保证。

本轮预算4未改、新C11未触顶；补充同源码候选旧DG记录的第五次拒绝/incomplete，不加入新运行分母。C06虽主结论15日正确，却附加未记录截至日来源的逾期判断；两条失败都未修复。下一步仅建议独立回归及依据/结束约束验证，不在验收中优化。

按需改写未证明稳定收益；D/G是提示策略；主动关联冲突来源补查未实现；简单问题可能追查触顶。候选不具有程序语义保证或生产可靠性保证。本批比例仅描述这组运行。''')
append('docs/02-solution.md','''## 最终候选与默认行为

CLI默认仍dedup＋original门槛，`--demand-rewrite`和`--dg-targeted`默认关闭；最终候选演示显式传`--match-threshold one_overlap --dg-targeted`，不传demand-rewrite。`scripts/submission_demo.py`只选择输入和配置，工具路径由模型自主决定。单Agent的search/read预算每轮4次，无新增模型裁判；D/G只追加分类/回答/结束提示。主动关联冲突来源补查尚未实现。

框架职责为AgentScope 2.0.11提供ReAct循环、模型工具协议和会话维护；本项目提供检索/去重/门槛、故障观察、调用上限和公开Trace。原提示、可选改写、DG提示、原/放宽门槛均可明确选择。真实原文候选不等于自动语义验证。''')
p=root/'docs/04-ai-usage.md';text=p.read_text(encoding='utf-8').replace('提供本地模型配置，实际运行并审阅命令、答案、Trace 与 Git 提交内容。','提供本地模型配置；亲自运行、审阅和修改的具体范围待候选人本人确认，不将AI执行视为本人独立完成。');p.write_text(text,encoding='utf-8')
append('docs/04-ai-usage.md','''## 本轮及系列实验的AI辅助范围（2026-11-11）

检索基线、原Agent基线、去重与来源呈现、按需改写、门槛诊断/对照、D/G策略及最终候选验收的运行器、代码/测试、结果采集、语义复核和交付文档由Codex辅助编写及执行。真实模型deepseek-flash产生业务决策与回答；Codex复核实际工具返回和最终答案，不是独立人工评审或额外模型裁判。候选人提供题目、方向、合成测试与约束，但未有证据证明其亲自独立完成全部代码/测试/复核。

本轮Codex实际执行26项自动测试及19次真实验收，全部结果与失败保留，候选人尚需亲自复查、运行并解释关键代码。历史“11项”指早期版本，当前日志为26项。个人修改清单、实际亲自执行的命令、复核结论、总投入用时均待候选人补充；没有记录的用时不编造。未提交或推送Git。''')
append('docs/05-retrospective.md','''## 最终验收后的待复盘项（AI辅助整理）

召回齐全不能保证回答有据，提示中禁止的“同层级”仍在顺序变体出现；明确替代场景又产生用户未问的逾期判断。简单问题仍可能过度检索触顶。下一轮应围绕实际失败提出最小可检验修复，而不是继续堆叠大范围改动。以上为AI辅助归纳，候选人的独立学习收获、最难问题及实际用时待本人补充，不写成其已独立完成的经历。''')
print('Updated delivery documents; candidate source unchanged')
