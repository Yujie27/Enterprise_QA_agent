# A＋去重 独立实验

仅改变候选整理：原匹配候选→精确证据折叠→原排序→Top-k。提示词、模型、同义词、匹配门槛、分数公式、默认k和每轮4次工具预算均未改。
起始commit与工作区已有差异、业务代码和所有历史结果哈希见before.json；执行前封存，历史文件保持原样。

## 实现边界

原文、scope、version、effective_from严格相等才属于内容组。copied_from必须指向实际存在、唯一匹配、非转载的原始条款；已通过原匹配门槛的原始候选可作为代表，不以副本数量加分，不绕过门槛取未匹配的原件。没有转载字段的相同内容仅标content_duplicate_only。来源缺失或不一致的声明保留为独立候选，标unverified_copy；不编造来源。
不同数字、时间单位、否定、起算点、范围、例外或版本日期因精确文本/元数据不同而保留；同文档两个冲突section不合并。source_info返回实际成员ID、声明的来源及核验状态，让模型只按可见信息叙述来源。此实现保守，不进行语义近似去重。

## 工程验证

已有11项及新增6项共17项测试通过，见tests.json。首轮沙箱临时目录权限失败被保留说明，沙箱外同代码17/17通过。新增测试见tests/test_dedup.py。
独立开发变体：zeta/omega、17份archive-*转载，不使用COPY前缀；实际k=3/5/10均取得两个原始规则，k=1只一个。development_variant.json和development_results.json保存原始输入与实际输出，不纳入冻结27用例分母。

## 冻结检索对照

Gold未改，SHA256 `b9a951d8744804d9c9b5427ae753ccd8b143d8ab6865c90944e6e080de672c0a`。27用例×4k=108次调用；R05探索性排除，正例25题37条款、冲突9题。保持原始问题，各用例独立加载指定语料。
|k|A Recall宏→A＋去重|A Recall微→A＋去重|冲突完整A→A＋去重|来源折叠冲突完整A→A＋去重|
|---|---|---|---|---|
|1|74%→76%|64.86%→67.57%|0/9→0/9|0/9→0/9|
|3|94%→98%|91.89%→97.30%|8/9→9/9|8/9→9/9|
|5|94%→98%|91.89%→97.30%|8/9→9/9|8/9→9/9|
|10|98%→98%|97.30%→97.30%|9/9→9/9|9/9→9/9|

来源折叠后的必要证据Recall宏平均（每个原始条款最多计一次）：

|k|A|A＋去重|
|---|---|---|
|1|76%|76%|
|3|96%|98%|
|5|96%|98%|
|10|98%|98%|

C13：k=5从5份15日副本、严格Recall=0/2（按来源折叠后1/2），变为真实D01/30日与D02/15日两个代表、严格和折叠Recall均2/2。没有把gold改成只需命中一个来源。k=1容量仍不足双方，不能判冲突证据完整。
逐例候选与前后指标在retrieval_results.jsonl；必要证据Recall退化列表：[]

|用例|k|返回候选是否变化（含来源元数据）|严格Recall前→后|折叠来源Recall前→后|
|---|---|---|---|---|
|C13|1|是|0.0→0.5|0.5→0.5|
|C13|3|是|0.0→1.0|0.5→1.0|
|C13|5|是|0.0→1.0|0.5→1.0|
|C13|10|是|1.0→1.0|1.0→1.0|
|X01|3|是|1.0→1.0|1.0→1.0|
|X01|5|是|1.0→1.0|1.0→1.0|
|X01|10|是|1.0→1.0|1.0→1.0|
|X02|3|是|1.0→1.0|1.0→1.0|
|X02|5|是|1.0→1.0|1.0→1.0|
|X02|10|是|1.0→1.0|1.0→1.0|
|X03|3|是|1.0→1.0|1.0→1.0|
|X03|5|是|1.0→1.0|1.0→1.0|
|X03|10|是|1.0→1.0|1.0→1.0|

除C13外，X01—X03的重复预算噪声也被内容折叠，候选减少但必要证据未退化。C11原始查询仍只有D01，D04词项门槛问题未被去重修复。其他用例实际候选不变。

## 18次真实Agent对照

复用原Agent运行器和语料：12个场景，各一次；C01/C11/C13额外两次。模型deepseek-flash，配置与A清单逐字段相等，温度/top_p/seed仍为服务默认；4次每轮工具预算未增。全部18次实际运行，0次未执行，无Mock。
业务通过和执行完成分开：A业务10/18；A＋去重业务16/18；同时执行结束且业务通过14/18。两次incomplete不伪称正常完成，即使已有答案可由已取得证据支持。
|运行|A业务通过|A＋去重业务通过|执行状态|工具数|证据完整|判定和Trace|
|---|---|---|---|---|---|---|
|R01_r1|True|True|completed|2|True|[Trace](agent/sessions/R01_r1/traces/20261110_204911_887183.json)；仅有D01，读取后引用费用发生后30日并限定证据范围；无单证据拒答退化。|
|R06_r1|True|True|completed|2|None|[Trace](agent/sessions/R06_r1/traces/20261110_204913_900647.json)；两次搜索得到排除性D01，未将普通报销30日迁移到育儿补贴，说明申请办法未提供。|
|R07_r1|True|True|completed|3|True|[Trace](agent/sessions/R07_r1/traces/20261110_204920_988248.json)；实际见研发D01/销售D02的scope，正确区分15/20日期限；未基于编号宣称优先。|
|C01_r1|True|True|completed|3|True|[Trace](agent/sessions/C01_r1/traces/20261110_204921_954985.json)；读取双方并列30/15日，请求确认范围或优先级，未建议先选某一期限。|
|C02_r1|True|True|completed|2|True|[Trace](agent/sessions/C02_r1/traces/20261110_204928_574257.json)；唯一D01可据原文答30日，同时说明日历定义和范围未提供。|
|C05_r1|False|True|completed|3|True|[Trace](agent/sessions/C05_r1/traces/20261110_204931_197796.json)；列出新旧日期差异和30/15冲突，核对双方后请求适用/替代依据，未仅凭新日期选15日，也没有附加先按15日的建议。与A的差异不能归因去重：此语料没有重复候选。|
|C11_r1|False|True|completed|4|True|[Trace](agent/sessions/C11_r1/traces/20261110_204937_964835.json)；自主二次查询加入费用报销取得D04，再读D01/D04，正确回答30日和合规票据；未扩展其他材料和计算口径。此语料无重复，检索候选对应同一查询没有变化，差异属于真实模型运行波动。|
|C12_r1|True|True|completed|2|True|[Trace](agent/sessions/C12_r1/traces/20261110_204939_455353.json)；D01-S1与D01-S2分别保留并可见；读取后按条款列出冲突，请求确认。|
|C13_r1|False|True|completed|3|True|[Trace](agent/sessions/C13_r1/traces/20261110_204947_091265.json)；首次limit5实际取得D01-S1与D02-S1，D02.source_info显示8个已核验转载来源。随后读双方，并列冲突、拒绝以副本数量裁决，请求确认，未建议先按15日执行。|
|M01_r1|True|True|completed|4|True|[Trace](agent/sessions/M01_r1/traces/20261110_204954_874418.json)；首轮4次调用取得范围不同的D01/D02，第二轮结合用户研发差旅补充与首轮可见证据回答返程后15日；没有丢失上下文。|
|E03_r1|True|True|completed|4|True|[Trace](agent/sessions/E03_r1/traces/20261110_204958_957488.json)；读取D01并查定义后明确日历口径未知，没有推荐按工作日或自然日执行；存在泛化风险提醒，但未设定具体未提供的计算规则。|
|F01_r1|True|False|tool_error|2|None|[Trace](agent/sessions/F01_r1/traces/20261110_205003_126900.json)；正确区分工具失败和制度不存在，没有给期限数字，但补造错误发生时间并标注UTC。实际工具文本没有提供该时间，故属于主结论正确但附带无依据细节，非去重造成的检索退化。|
|C01_r2|False|False|completed|3|True|[Trace](agent/sessions/C01_r2/traces/20261110_205014_328478.json)；两条证据齐全、冲突说明正确，却建议先按15日处理，另声称效力层级相同；原文没有层级或优先级依据。|
|C01_r3|True|True|completed|3|True|[Trace](agent/sessions/C01_r3/traces/20261110_205014_117514.json)；双方可见且核对原文，正确并列冲突并请求确认；未选定期限。|
|C11_r2|False|True|incomplete|4|True|[Trace](agent/sessions/C11_r2/traces/20261110_205026_075239.json)；预算内已搜索取得并读取D01与D04，答案正确引用30日及合规票据，并保留未给出的材料细则。第5次额外核对被拒，执行必须记incomplete，但现有业务答案有据；不计入同时执行完成且业务通过。|
|C11_r3|False|True|incomplete|4|True|[Trace](agent/sessions/C11_r3/traces/20261110_205025_105701.json)；原文证据齐全，期限与票据回答均有来源，无次日起算补造。额外追查材料细则触发第5次请求拒绝，执行incomplete单列，不掩盖或增加预算重跑。|
|C13_r2|False|True|completed|3|True|[Trace](agent/sessions/C13_r2/traces/20261110_205034_218660.json)；首次limit5取得双方；source_info实际展示所有已验证副本的来源，读取双方后并列冲突并请求确认，无15日执行建议。|
|C13_r3|False|True|completed|3|True|[Trace](agent/sessions/C13_r3/traces/20261110_205035_324939.json)；双方原文及副本核验信息均真实可见，最终说明无法确定期限并请求确认，未将副本数量作为权威。末句把读取和搜索笼统说成两次检索不够精确，记录为叙述瑕疵，不影响原文引用与来源核验结论。|

### 核心结论

1. **去重解决了本次C13的重复候选挤占**：检索k=5严格与折叠证据覆盖0/2、1/2→2/2；Agent三次均首次取得D01与D02，读取双方后并列冲突、请求确认，没有先按15日执行的建议。来源信息由实际source_info提供，八个副本的描述可以复核。C13最终业务0/3→3/3。
2. **冲突覆盖改善**：冻结9题在k=3/5由8/9→9/9，k=1仍0/9，k=10仍9/9。主指标严格原始doc+section；来源折叠指标另列，没有用副本数量提高分数。
3. **回答改善但非全部可归因去重**：C13的候选变化与取得冲突双方有直接可见链条。C11语料没有重复，原始查询检索仍漏D04，本次三次Agent自主改写碰巧都取得材料，不能归因去重；其中两次额外追查触顶incomplete。C05本次不再先建议15日，同样无检索变化，属于采样波动。
4. **仍有回答约束和工程预算问题**：C01_r2仍建议先按15日，提示词没有修。F01_r1正确识别故障但编造发生时间并标UTC，严格业务不通过，是相对A的新退化；故障返回文本不含该时间。E03未补造工作日/自然日口径，M01继承上下文，单证据R01/C02正常。
后续B可单独验证材料/票据的词汇与多意图召回；C可单独验证独立冲突来源补查；D或回答依据约束应检查无依据执行建议、起算口径、错误时间和过度查证后的预算不足。上述都没有混入“A＋去重”。

## 复现

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts/dedup_experiment.py retrieval --output examples/evaluation/a_plus_dedup/replay_retrieval01
.\.venv\Scripts\python.exe -B scripts/agent_baseline.py prepare --run-dir examples/evaluation/a_plus_dedup/replay01
.\.venv\Scripts\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/a_plus_dedup/replay01 --batch primary
.\.venv\Scripts\python.exe -B scripts/agent_baseline.py run --run-dir examples/evaluation/a_plus_dedup/replay01 --batch repeats
.\.venv\Scripts\python.exe -B scripts/collect_agent_baseline.py --run-dir examples/evaluation/a_plus_dedup/replay01
```

完整记录在agent/results.jsonl，逐次语义核验在agent/reviews.json；原始CLI Trace与ToolResponse在agent/sessions。判断只使用实际可见证据，没有向模型补充gold。
本实验小样本、模型服务默认采样未固定，其他不含重复的用例波动不能断言是去重带来的因果改善。全部历史结果保持原样，不提交或推送Git。
