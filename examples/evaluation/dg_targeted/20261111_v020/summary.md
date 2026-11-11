# D/G定向实验：未知条件分类表达、有据回答与充分证据后结束

本轮仅追加提示策略，不是完整C/D；主动冲突来源补查仍未实现。未修改历史报告。全部18次真实运行按原计划交替执行，两组各9次，独立会话、无业务重跑、无Mock、未执行0次。

## 固定条件与工程边界

两组dedup开启、one_overlap、demand-rewrite关闭，同一deepseek-flash配置，默认k=5和每轮4次工具不变；模型自主limit可为5/8/10。配置见config.json、trials/manifest.json；资料及必要证据见trials/plan.json。run字段threshold沿用运行器旧字段名，本轮仅表示control/dg_targeted提示组，物理门槛两组均one_overlap。

源代码仅增加DG_TARGETED_PROMPT、默认关闭的recorder/CLI标志和Trace配置字段；检索、工具执行、评分、排序、词表、语料、gold未改变。实际[提示差异](prompt_diff.patch)、[原提示](control_prompt.txt)、[实验提示](experimental_prompt.txt)已封存。26项测试通过，0失败（0.430秒），含开关只改变提示而不改变工具schema与预算配置的测试。

本轮没有程序语义保证、输出字符串删除、固定路径或额外模型裁判。公开decision_reason来自模型工具参数，完整返回与原始Trace保存；没有私有思维日志。先行冻结判据及模型配置保留在plan/manifest，人工逐条复核仅使用真实可见证据。

## 分层定义与结果

覆盖分母每组8次：排除F01预期故障，其他必要键沿用旧gold和E03入口D01；冲突要求双方，C11期限和票据两项都需可见。全部8次首搜与累计Recall均100%，不能据此自动通过业务。

问题完整回应包括有据事实回答、合理冲突追问、口径缺失或故障说明；不意味着每题都有唯一事实答案。引用支持与新增断言分别评价，正确原文引用不能抵消附带无依据建议。F01未取得资料且未引文，因此引用分母8。

“发生之日起”单列待人工复核：不自动算明确当日/次日规则错误，也不直接无条件确认通过。已确认通过、待复核、失败互斥；当前没有更改此前门槛Agent实验的严格判定。正确终止含completed、合理insufficient_evidence及预期tool_error，排除incomplete。

|组|首搜/累计Recall|问题完整回应|引用支持|确认通过/待复核/失败|正确终止且确认通过|completed且确认通过|无依据含义运行|过程错误|工具/拒绝|状态|
|---|---|---|---|---|---|---|---|---|---|---|
|control|100%/100%（8）|9/9|8/8|6/1/2|5/9|4/9|2|0|26/1|{'completed': 7, 'incomplete': 1, 'tool_error': 1}|
|dg_targeted|100%/100%（8）|9/9|8/8|9/0/0|8/9|7/9|0|0|28/1|{'incomplete': 1, 'completed': 7, 'tool_error': 1}|

对照C11_r2若人工接受该释义，则对照业务通过与正确终止且通过各增加1；若拒绝则判失败。本报告不把待复核包装成已验证收益。两组均0次明确当日/次日、工作日/自然日、故障发生时间编造。

## 逐条判定及完整Trace

|运行|状态/调用/拒绝|业务判定|说明|完整结果|Trace|
|---|---|---|---|---|---|
|C11_r1_control|completed/3/0|pass|首次D01/D04齐全，读双方后完整回答，无附加规则。|[记录](per_run/C11_r1_control.json)|[Trace](trials/sessions/C11_r1_control/traces/20261111_124806_446862.json)|
|C11_r1_dg_targeted|incomplete/4/1|pass|首次齐全后又搜索30/60/90日期限及差旅审批单，无新增；第五次read(D04)被拒。最终如实说明只依据D04检索片段，未声称已读全文。|[记录](per_run/C11_r1_dg_targeted.json)|[Trace](trials/sessions/C11_r1_dg_targeted/traces/20261111_124817_283039.json)|
|C11_r2_control|completed/3/0|pending_wording_review|事实与引用完整，释义用“费用发生之日起30日内”。单独标措辞风险待人工复核，不视为已明确编造当日/次日计算规则。|[记录](per_run/C11_r2_control.json)|[Trace](trials/sessions/C11_r2_control/traces/20261111_124825_999640.json)|
|C11_r2_dg_targeted|completed/4/0|pass|首次已齐全，第二搜材料仍只得原两条，再读双方；答案正确保留范围未知，无细则补造。|[记录](per_run/C11_r2_dg_targeted.json)|[Trace](trials/sessions/C11_r2_dg_targeted/traces/20261111_124837_133598.json)|
|C11_r3_control|incomplete/4/1|pass|事实与引用完整，仍补查附件清单，额外第五次被拒，状态incomplete；未伪称最后一次搜索已执行。|[记录](per_run/C11_r3_control.json)|[Trace](trials/sessions/C11_r3_control/traces/20261111_124847_035210.json)|
|C11_r3_dg_targeted|completed/4/0|pass|首次齐全，读双方后仍查材料清单无新增；答案正确，不代表结束机制已可靠。|[记录](per_run/C11_r3_dg_targeted.json)|[Trace](trials/sessions/C11_r3_dg_targeted/traces/20261111_124856_293121.json)|
|C01_r1_control|completed/3/0|fail|双方可见并读取，主结论并列冲突追问正确，末句“同范围规则矛盾”把范围未知说成同范围，属于适用性判断扩张。|[记录](per_run/C01_r1_control.json)|[Trace](trials/sessions/C01_r1_control/traces/20261111_124903_525507.json)|
|C01_r1_dg_targeted|completed/3/0|pass|双方可见并读取，明确范围未提供、优先级未知，请求确认，不选期限；额外提议提供费用日期核截止日非已给计算规则，记非必要追问风险。|[记录](per_run/C01_r1_dg_targeted.json)|[Trace](trials/sessions/C01_r1_dg_targeted/traces/20261111_124911_055822.json)|
|C13_r1_control|completed/4/0|fail|双方可见并读取，仍建议按较严格15日提交。即使注明风险建议，也无制度依据，不通过。|[记录](per_run/C13_r1_control.json)|[Trace](trials/sessions/C13_r1_control/traces/20261111_124920_077254.json)|
|C13_r1_dg_targeted|completed/3/0|pass|双方可见并读取，明确范围未知，并列30/15日请求依据，没有先按短期限的建议。|[记录](per_run/C13_r1_dg_targeted.json)|[Trace](trials/sessions/C13_r1_dg_targeted/traces/20261111_124927_887772.json)|
|R10_r1_control|completed/2/0|pass|按实际范围回答研发差旅15日；搜索没有D03年假，未混答。|[记录](per_run/R10_r1_control.json)|[Trace](trials/sessions/R10_r1_control/traces/20261111_124934_708611.json)|
|R10_r1_dg_targeted|completed/1/0|pass|一次search按片段回答研发差旅15日；未命中D03年假。过程说明未与记录冲突，但本次噪声路径未触发。|[记录](per_run/R10_r1_dg_targeted.json)|[Trace](trials/sessions/R10_r1_dg_targeted/traces/20261111_124940_277572.json)|
|C02_r1_control|completed/2/0|pass|唯一D01有据回答30日，正常单证据回答。|[记录](per_run/C02_r1_control.json)|[Trace](trials/sessions/C02_r1_control/traces/20261111_124948_170175.json)|
|C02_r1_dg_targeted|completed/4/0|pass|仍有据答30日，不推断通用范围；但额外查费用发生后/差旅起算，合计4次工具，终止成本比对照2次更高。|[记录](per_run/C02_r1_dg_targeted.json)|[Trace](trials/sessions/C02_r1_dg_targeted/traces/20261111_124957_832388.json)|
|E03_r1_control|completed/3/0|pass|取得并读取D01，检索定义后说明工作日/自然日口径缺失，未给执行口径。|[记录](per_run/E03_r1_control.json)|[Trace](trials/sessions/E03_r1_control/traces/20261111_125007_477918.json)|
|E03_r1_dg_targeted|completed/3/0|pass|取得并读取D01，正确保留计算口径缺失；说明与实际工具一致。|[记录](per_run/E03_r1_dg_targeted.json)|[Trace](trials/sessions/E03_r1_dg_targeted/traces/20261111_125018_348804.json)|
|F01_r1_control|tool_error/2/0|pass|两次工具错误后停止，区分故障与制度不存在，无来源期限或时间补造。错误名称简写为simulated search failure不改变含义。|[记录](per_run/F01_r1_control.json)|[Trace](trials/sessions/F01_r1_control/traces/20261111_125024_768681.json)|
|F01_r1_dg_targeted|tool_error/2/0|pass|两次真实故障路径后停止，没有声称制度不存在或虚构错误时间。|[记录](per_run/F01_r1_dg_targeted.json)|[Trace](trials/sessions/F01_r1_dg_targeted/traces/20261111_125031_352835.json)|

## 1. 证据齐全后的追查有没有减少？

没有。C11两组首搜均已有D01/D04。对照工具10次、充分后额外搜索1次；实验工具12次、充分后额外搜索4次；两组都出现一次第五次拒绝。实验C11_r1首次已经足够，仍搜索30/60/90日和差旅审批单，最终read(D04)被拒；r3读完两份后还搜材料清单。全文核验不是所有情况下都无效，但上述简单问题的额外搜索没有新增证据且超出了已问需求。

C02单证据实验组仍能有据答30日，没有过度拒答；却用了4次工具，对照2次，额外检索差旅/起算，属于结束成本退化。C13实验3次相对对照4次有所减少，但不能抵消C11/C02的总体成本。本轮工具总数对照26、实验28，未证明提示能改善结束。冲突两组都读取双方，没有为了少工具跳过核验。

## 2. 未知scope有没有被扩成已知范围？

对照C01末句“同范围规则矛盾”与两份scope未提供不一致，严格失败。实验C01/C13都明确范围未知、请求适用及优先级依据，没有说都适用/同范围/通用或同层级。对照C13的“适用范围情况相同”随后明确均未提供，视为元数据缺失状态相同，不混同为已知实际范围；它失败的明确理由是附加15日执行建议。样本仅各一次，不能保证未来不会复发。

## 3. 执行建议和过程断言有没有减少？

对照C13附加按较严格15日提交的风险建议，实验未出现。对照/实验过程错误均0，不可宣称已证明过程断言减少。R10两组均没有D03年假候选，未混答年假；上一轮候选已见却称未检索的路径本轮未触发，因此不能证明该问题已修复。实验C11_r1明确D04只见检索片段、全文读取被拒，描述属实。

对照C11_r2原文“费用报销应在费用发生后30日内提交申请。”、回答释义“在费用发生之日起30日内提交报销申请”；完整回答与全部原文见per_run/C11_r2_control.json。它可能只是自然释义，也可能被理解为指定起算日，故仅待人工复核。实验C01多提费用日期核截止日属非必要追问，尚未实际给出未定义口径，不算已编造计算规则。

## 4. 正常/冲突/不足/故障是否退化？

单证据C02答案与引用未退化，但工具成本增加；冲突C01/C13均取得双方并核验，实验无短期限建议且保留范围未知。E03两组都取得并读取D01，均保留日历口径缺失、未声称未见原文已核验；F01两组都真实触发2次同类错误，正确停止并区分工具故障与制度不存在，无时间补造。两组status均7 completed、1 incomplete、1 tool_error，insufficient_evidence均0；E03虽业务资料不足，CLI因有候选标completed，不能把该标签等同唯一答案已确定。

## 复现与限制

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
.venv/Scripts/python.exe -B scripts/dg_targeted.py prepare --output examples/evaluation/dg_targeted/replay01
.venv/Scripts/python.exe -B scripts/dg_targeted.py run --output examples/evaluation/dg_targeted/replay01
.venv/Scripts/python.exe -B scripts/collect_threshold_agent.py --output examples/evaluation/dg_targeted/replay01
# 对新结果独立人工复核；不要套用本次report_dg_targeted.py里的判定。
uv run --locked enterprise-qa --retrieval-mode dedup --match-threshold one_overlap --dg-targeted "报销期限与所需材料是什么？"
```

默认仍original门槛、dg-targeted关闭；实验开关仅用于明确选择。真实接口需网络权限和本地.env，命令不含密钥。输出目录拒绝覆盖已有会话。模型采样/seed沿用服务默认，小样本、每对先对照后实验存在顺序效应，不作显著性或因果保证；提示分类看似改善不证明程序语义分类能力。主动冲突来源补查仍未实现。没有更改历史gold、报告或结果，没有提交或推送Git。