# 最终候选验收：有保留结论

候选具备可复现演示链路，但不能写成所有验收无缺陷通过。原生18次严格业务17/18，受控返回顺序变体1次未严格通过；共19次真实运行，全部保留，无Mock、无业务重跑。另复用同源码候选既有预算触顶记录1条，明确不算新增运行。小样本不是泛化准确率或生产可靠性指标。

## 候选封存与条件

commit `038f3f20119c1c4ef062390bf80faaf461ad59b1` 只标识历史提交；本次未提交候选以[identity.json](candidate/identity.json)的文件哈希集合标识，标识SHA256：`ea8fa25de595f222f1dedb83c497772b4933ab0e7a51407b585cae151f641b04`。封存目录包含完整src、pyproject.toml、uv.lock、.env.example、工作区实际补丁、已选提示词和模型配置；实际资料哈希逐条在trials/plan.json。验收期间业务代码未改，旧实验哈希保持不变。

配置：dedup=True、match_threshold=one_overlap、dg_targeted=True、demand_rewrite=False；deepseek-flash，经本地.env的OpenAI兼容端点，具体非敏感参数及依赖版本在config/manifest。默认工具每轮4次，模型自主limit未限制为5，k默认值仍5。M01同一CLI interactive会话；其余独立进程。模型temperature/top_p/seed未显式设置。候选CLI默认仍dedup＋original门槛、DG关闭、改写关闭，候选通过显式演示入口选取，未切换全局默认。

26项自动测试通过（tests.log），测试不证明真实模型所有输出都正确。19次都实际取得模型回复，无未执行；预算为4且未改；本轮没有第五次请求，用同候选旧记录补充验证明确incomplete。

## 逐条真实运行与分层判定

completed仅是执行标签。本轮原生16 completed、2 tool_error；受控变体completed；新运行0 incomplete、0 insufficient_evidence。R06业务资料不足但CLI由于有边界候选标completed。F01/F02合理故障说明可业务通过，但不能当已核验制度的事实回答。所有正常执行标签不能掩盖附加断言错误。

|运行|状态/工具|业务类别/判定|依据与限制|完整结果|Trace|
|---|---|---|---|---|---|
|R01_native|completed/2|完整有据回答；True|读取唯一D01，有据答费用发生后30日，范围未知。|[记录](per_run/R01_native.json)|[Trace](trials/sessions/R01_native/traces/20261111_131347_215013.json)|
|C01_native|completed/3|合理冲突追问；True|30/15日双方可见并读取，范围/优先级未知，合理冲突追问。|[记录](per_run/C01_native.json)|[Trace](trials/sessions/C01_native/traces/20261111_131355_526095.json)|
|C02_native|completed/3|完整有据回答；True|与C01完全相同问题，仅保留D01后答30日，未过度拒答。|[记录](per_run/C02_native.json)|[Trace](trials/sessions/C02_native/traces/20261111_131407_921209.json)|
|R06_native|completed/2|合理资料不足说明；True|相关候选是排除性边界，说明无法提供育儿补贴申请办法，未把30日迁移为补贴期限。|[记录](per_run/R06_native.json)|[Trace](trials/sessions/R06_native/traces/20261111_131417_586418.json)|
|R02_native|completed/2|完整有据回答；True|模型自主处理出差/回来/费用申请改写，按研发差旅scope回答返程15日。|[记录](per_run/R02_native.json)|[Trace](trials/sessions/R02_native/traces/20261111_131427_568599.json)|
|M01_native|completed/3|完整有据回答；True|原interactive同一Agent会话，两轮输入；正确继承研发部门及差旅类型，引用D02返程15日。|[记录](per_run/M01_native.json)|[Trace](trials/sessions/M01_native/traces/20261111_131440_926558.json)|
|F01_native|tool_error/2|合理工具故障说明；True|两次实际search错误后停止，没有据失败推断制度不存在。|[记录](per_run/F01_native.json)|[Trace](trials/sessions/F01_native/traces/20261111_131448_915637.json)|
|F02_native|tool_error/4|合理工具故障说明；True|实际read(D01)/read(D02)两次均错误，依据search片段列双方，明确原文核验失败；读取故障已触发。|[记录](per_run/F02_native.json)|[Trace](trials/sessions/F02_native/traces/20261111_131457_390491.json)|
|C05_native|completed/3|合理冲突追问；True|较新日期没有替代依据，仍并列30/15日追问，没有仅凭日期裁决。|[记录](per_run/C05_native.json)|[Trace](trials/sessions/C05_native/traces/20261111_131506_641299.json)|
|C06_native|completed/4|无依据附带结论；False|明确替代及发生日期支持15日主结论，但附加未由本次用户/工具提供的截至日期及逾期判断；主答案正确，严格依据判定不通过，不声称日期数值本身错误。|[记录](per_run/C06_native.json)|[Trace](trials/sessions/C06_native/traces/20261111_131516_960310.json)|
|C09_native|completed/4|合理冲突追问；True|工作日/自然日虽数字同为15，仍指出实质差异并追问；两份范围确实相同。|[记录](per_run/C09_native.json)|[Trace](trials/sessions/C09_native/traces/20261111_131526_680351.json)|
|C10_native|completed/3|合理冲突追问；True|区分费用发生后/返程后两个起算点，引用双方请求依据。|[记录](per_run/C10_native.json)|[Trace](trials/sessions/C10_native/traces/20261111_131536_243608.json)|
|C12_native|completed/2|合理冲突追问；True|同文档S1/S2都可见，明确30/15日内部冲突，未按位置选答案。|[记录](per_run/C12_native.json)|[Trace](trials/sessions/C12_native/traces/20261111_131544_811715.json)|
|C13_native|completed/4|合理冲突追问；True|去重后双方可见且读取；副本来源由实际source_info支持，不按副本数裁决。|[记录](per_run/C13_native.json)|[Trace](trials/sessions/C13_native/traces/20261111_131553_472353.json)|
|X06_native|completed/1|完整有据回答；True|同ID D01原文45日可见，回答随当前资料变成45日，不沿用30日。|[记录](per_run/X06_native.json)|[Trace](trials/sessions/X06_native/traces/20261111_131601_791664.json)|
|X04_native|completed/3|合理冲突追问；True|文件顺序变换，但实际首搜顺序仍D01,D02，变换未触发；本次冲突结论正确，不宣称验证了返回位置鲁棒性。|[记录](per_run/X04_native.json)|[Trace](trials/sessions/X04_native/traces/20261111_131611_478475.json)|
|X05_native|completed/3|合理冲突追问；True|实际候选A01/15日、Z99/30日，引用新编号并列冲突，无旧ID误引。|[记录](per_run/X05_native.json)|[Trace](trials/sessions/X05_native/traces/20261111_131619_848196.json)|
|C11_native|completed/4|完整有据回答；True|首次片段已经覆盖期限/票据，之后又搜材料并读双方，共4次；答案有据，未触发第五次；仍有额外追查成本。|[记录](per_run/C11_native.json)|[Trace](trials/sessions/C11_native/traces/20261111_131630_570192.json)|
|C01_reverse|completed/3|无依据附带结论；False|受控顺序反转后主结论正确，但说“两条同层级冲突条款”；资料没有层级依据，违反未知层级表达约束。|[记录](per_run/C01_reverse.json)|[Trace](trials/sessions/C01_reverse/traces/20261111_131638_767443.json)|

所有per_run保存实际输入、查询参数、完整返回、公开理由、最终回答、原始引用文本、必要证据缺口、业务判定及状态；M01额外保存完整conversation。工具原始ToolResponse及reply_metadata在各sessions目录，没有私有思维日志。

## 覆盖与成对变换

- 原题30/15日无范围/优先级：C01；同一问题只留D01：C02。两者问题字符串相同，答案分别冲突追问/30日。R01与X06同题、同ID，工具文本实际30→45，回答随之变为45。详见transformations.json。
- F01搜索故障和F02读取故障均实际触发；F02分别调用read(D01)、read(D02)且都失败，最终如实说未完成原文核验，没有假称读取成功。
- X04文件顺序变化后，实际首搜仍D01/30、D02/15，现有排序抵消，标“变换未触发”。X05改号后实际A01/15、Z99/30，语义条款顺序随编号排序改变；回答仍列双方，未误引旧编号。
- C01_reverse是隔离评测适配器在原search得到Top-k之后反转同一候选数组，候选业务代码未改；before/after及实际返回可核查。与原生配置分开报告，不能把受控工具变体称完全原生。真实顺序变化后，模型仍并列冲突，但补造“同层级”，严格失败，故不能保证顺序鲁棒性。
- 同一候选既有预算上限：[补充记录](supplemental_budget.json)，源Trace为此前DG实验C11_r1_dg_targeted。核对所有src哈希相等，4次后第五次read(D04)被拒、status=incomplete；事实答案有据但执行未完成。不是本轮新运行，不通过减预算或反复抽样制造触顶。

## 关键问题与最小建议（未实施）

1. C06主结论15日正确，但附加“截至2026年11月11日……如尚未提交，已超过期限”。本次用户和业务工具没有给当前截至日，也没有问是否逾期；日期数值本身并非这里认定错误，失败在超出证据/问题范围的执行判断。最小下一步建议是单独测试“仅答所问期限，不主动计算当前是否逾期”的约束，并要求需要代算时由用户提供截至日及计算口径；本轮不修改候选。
2. C01_reverse明确说“两条同层级冲突条款”，而原文没有效力层级。D/G虽已有禁止规则仍会违反，说明不是程序语义保证。最小下一步是独立增加该失败的回归例和依据约束验证；不要宣称简单再加一句提示就已修复，也不在本轮引入大规模优化。
3. 简单C11首次片段齐全后仍有额外材料搜索；同候选预算记录证明会触顶。需后续单独评估覆盖状态和结束约束。本轮不变更4次预算，不拿本轮未触顶当问题消失。

## 评审演示与复现

提交演示使用scripts/submission_demo.py，直接调用真实CLI并显式选择候选，不含固定答案或固定工具路径；它的--help已离线检查，没有另跑模型来替换验收记录。运行时可以产生新的结果，不保证与已保存答案逐字相同。

```powershell
uv sync --locked
Copy-Item .env.example .env
# 在本地.env填写模型配置，绝不提交密钥
uv run --locked python scripts/submission_demo.py normal
uv run --locked python scripts/submission_demo.py conflict
uv run --locked python scripts/submission_demo.py single
uv run --locked python scripts/submission_demo.py replace45
uv run --locked python scripts/submission_demo.py multi
uv run --locked python scripts/submission_demo.py read-failure
# 完整重新验收使用全新目录；保持候选源码和README直到运行结束都不改：
.venv/Scripts/python.exe -B scripts/final_acceptance.py prepare --output examples/evaluation/final_acceptance/replay01
.venv/Scripts/python.exe -B scripts/final_acceptance.py run --output examples/evaluation/final_acceptance/replay01
.venv/Scripts/python.exe -B scripts/collect_threshold_agent.py --output examples/evaluation/final_acceptance/replay01
# 新输出须独立人工复核；report_final_acceptance.py含本次人工判定，不可套用。
```

AgentScope 2.0.11负责模型调用、工具schema、ReAct循环、会话消息及权限接入；本项目负责本地检索/去重/门槛、工具调用预算、故障入口与Trace。模型负责自主查询、读取、追问或结束。Mock是已有脚本式流程示意，只检查本地链路，不证明决策效果；无模型时不得把Mock作为本次候选成功记录。

## 交付边界

按需改写未证明稳定收益，候选关闭；D/G只是提示策略；主动关联冲突来源补查尚未实现；简单问题仍可能过度追查触顶。本批变化不代表一般正确率。当前资料合成、检索词项粗糙，无生产文档接入、程序语义/断言校验或部署可靠性保证。

代码、测试、评测运行器、语义复核与文档由AI辅助完成，候选人尚需亲自复查及解释；未记录的实际总用时待候选人补充，未将模型运行时长冒充个人投入。未提交或推送Git。历史实验报告原样保留；README及交付文档在全部运行/冻结校验完成后更新，候选业务源码不变。