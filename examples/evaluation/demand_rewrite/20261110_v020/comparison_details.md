# 逐场景对照与补充核验

旧结果只读取；本表不改变判定或gold。完整记录路径见Trace列，工具完整返回保存在相邻sessions目录。

|配置|场景|次数|首次完整|累计完整|业务通过|completed且通过|
|---|---|---|---|---|---|---|
|B|R01|1|1/1|1/1|1/1|1/1|
|B|R06|1|不适用|不适用|1/1|1/1|
|B|R07|1|1/1|1/1|1/1|1/1|
|B|C01|3|3/3|3/3|3/3|3/3|
|B|C02|1|1/1|1/1|1/1|1/1|
|B|C05|1|1/1|1/1|1/1|1/1|
|B|C11|3|0/3|1/3|1/3|1/3|
|B|C12|1|1/1|1/1|1/1|1/1|
|B|C13|3|0/3|0/3|0/3|0/3|
|B|M01|1|1/1|1/1|1/1|1/1|
|B|E03|1|0/1|0/1|1/1|0/1|
|B|F01|1|不适用|不适用|1/1|0/1|
|dedup_rewrite|R01|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|R06|1|不适用|不适用|1/1|1/1|
|dedup_rewrite|R07|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|C01|3|3/3|3/3|3/3|3/3|
|dedup_rewrite|C02|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|C05|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|C11|3|0/3|1/3|1/3|1/3|
|dedup_rewrite|C12|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|C13|3|3/3|3/3|2/3|2/3|
|dedup_rewrite|M01|1|1/1|1/1|1/1|1/1|
|dedup_rewrite|E03|1|0/1|0/1|1/1|0/1|
|dedup_rewrite|F01|1|不适用|不适用|1/1|0/1|

## C13实际返回与断言核验

|配置/运行|首次真实候选键|最终必要键缺口|业务|Trace|
|---|---|---|---|---|
|B/C13_r2|COPY0/COPY0-S1, COPY1/COPY1-S1, COPY2/COPY2-S1, COPY3/COPY3-S1, COPY4/COPY4-S1|D01/D01-S1|False|[记录](B/sessions/C13_r2/traces/20261110_211641_322228.json)|
|B/C13_r3|COPY0/COPY0-S1, COPY1/COPY1-S1, COPY2/COPY2-S1, COPY3/COPY3-S1, COPY4/COPY4-S1|D01/D01-S1, D02/D02-S1|False|[记录](B/sessions/C13_r3/traces/20261110_211646_127759.json)|
|B/C13_r1|COPY0/COPY0-S1, COPY1/COPY1-S1, COPY2/COPY2-S1, COPY3/COPY3-S1, COPY4/COPY4-S1|D01/D01-S1, D02/D02-S1|False|[记录](B_launcher_recovery/sessions/C13_r1/traces/20261110_211524_796491.json)|
|dedup_rewrite/C13_r1|D01/D01-S1, D02/D02-S1|无|True|[记录](dedup_rewrite/sessions/C13_r1/traces/20261110_211735_700734.json)|
|dedup_rewrite/C13_r2|D01/D01-S1, D02/D02-S1|无|True|[记录](dedup_rewrite/sessions/C13_r2/traces/20261110_211822_056035.json)|
|dedup_rewrite/C13_r3|D01/D01-S1, D02/D02-S1|无|False|[记录](dedup_rewrite/sessions/C13_r3/traces/20261110_211827_574994.json)|

组合r3的‘通用范围’原句、实际scope未提供和严格失败判定见[逐条结果](per_run/dedup_rewrite/C13_r3.json)。其主答案并列冲突并追问正确；未提供范围却被称通用，属于附带断言失败。C12措辞与此不同：同一文档未列范围差异，最终也说明范围缺失，不据此声称通用适用。

## 资料不足与多轮路径

|配置/场景|核验结论|实际记录|
|---|---|---|
|B/R07|实际见研发D01和销售D02的scope，按研发答返程15日；明确销售20日不适用。没有反事实控制，不能因果证明不依赖顺序。|[Trace](B/sessions/R07_r1/traces/20261110_210807_476043.json)|
|B/M01|核对两轮conversation：首轮区分非差旅普通费用与研发差旅，第二轮继承部门/费用类型，用已见D02回答返程15日。|[Trace](B_launcher_recovery/sessions/M01_r1/traces/20261110_211528_611521.json)|
|B/E03|两次实际返回为空，没有看到D01；正确保留日历口径未知、请求业务语境，不建议自然日或工作日。安全业务通过，但必要入口证据覆盖退化。|[Trace](B_launcher_recovery/sessions/E03_r1/traces/20261110_211533_827101.json)|
|B/F01|两次真实工具错误路径均触发，说明工具失败而非制度不存在；没有引用未见条款或编造发生时间。|[Trace](B_launcher_recovery/sessions/F01_r1/traces/20261110_211536_392067.json)|
|dedup_rewrite/R07|实际见研发D01和销售D02的scope，按研发答返程15日；明确销售20日不适用。没有反事实控制，不能因果证明不依赖顺序。|[Trace](dedup_rewrite/sessions/R07_r1/traces/20261110_211707_396477.json)|
|dedup_rewrite/M01|核对两轮conversation：首轮区分非差旅普通费用与研发差旅，第二轮继承部门/费用类型，用已见D02回答返程15日。|[Trace](dedup_rewrite/sessions/M01_r1/traces/20261110_211743_067407.json)|
|dedup_rewrite/E03|两次实际返回为空，没有看到D01；正确保留日历口径未知、请求业务语境，不建议自然日或工作日。安全业务通过，但必要入口证据覆盖退化。|[Trace](dedup_rewrite/sessions/E03_r1/traces/20261110_211746_450845.json)|
|dedup_rewrite/F01|两次真实工具错误路径均触发，说明工具失败而非制度不存在；没有引用未见条款或编造发生时间。|[Trace](dedup_rewrite/sessions/F01_r1/traces/20261110_211750_544890.json)|

开发题没有重复条款，同一查询在两种检索模式的结果相同。dev_B与dev_combo的差异来自模型自主路径/查询差异，不能归因于去重本身。DEV01的环节不确定性同时报告并从开发业务总体分母剔除；其两条原始证据的可见性仍可确定。

两组C11成功运行均在第二步已获得完整且含scope/版本/日期的原文片段，之后仍各读取两份：B_r2与组合_r3共4次读取，未增加必要条款。与先测r2的第五次拒绝一起说明，结束行为并未被机制可靠保证。

冻结清单字段勘误见[manifest_errata.json](manifest_errata.json)：pilot_C11的user_turn_count原写1（唯一用例轮数），实际计划/执行3次单轮。保留清单原字节，不据错误字段少算实际模型运行。
