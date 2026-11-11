# 最终候选：评审Trace索引

这些是已保存的真实结果，不是预设决策日志。提交演示用scripts/submission_demo.py；完整实验和失败原样在../evaluation，不重新挑选运行。

候选配置dedup＋one_overlap＋dg-targeted，demand-rewrite关闭，每轮4次工具；业务CLI默认未切换。

|评审项目|记录与状态|完整结果|原始Trace|
|---|---|---|---|
|正常回答|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/R01_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/R01_native/traces/20261111_131347_215013.json)|
|冲突核验并追问|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/C01_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/C01_native/traces/20261111_131355_526095.json)|
|同题只留D01|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/C02_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/C02_native/traces/20261111_131407_921209.json)|
|资料外问题|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/R06_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/R06_native/traces/20261111_131417_586418.json)|
|相似表达|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/R02_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/R02_native/traces/20261111_131427_568599.json)|
|同会话上下文|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/M01_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/M01_native/traces/20261111_131440_926558.json)|
|搜索故障|tool_error，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/F01_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/F01_native/traces/20261111_131448_915637.json)|
|读取故障已触发|tool_error，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/F02_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/F02_native/traces/20261111_131457_390491.json)|
|明确替代及附加逾期判断失败|completed，业务False|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/C06_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/C06_native/traces/20261111_131516_960310.json)|
|同ID换45日|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/X06_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/X06_native/traces/20261111_131601_791664.json)|
|编号改变|completed，业务True|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/X05_native.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/X05_native/traces/20261111_131619_848196.json)|
|返回顺序反转及层级断言失败|completed，业务False|[完整结果](../evaluation/final_acceptance/20261111_v020/per_run/C01_reverse.json)|[Trace](../evaluation/final_acceptance/20261111_v020/trials/sessions/C01_reverse/traces/20261111_131638_767443.json)|
|4次工具上限、明确未完成|同源码候选既有记录，incomplete；不计本轮新增分母|[来源与哈希核对](../evaluation/final_acceptance/20261111_v020/supplemental_budget.json)|[Trace](../evaluation/dg_targeted/20261111_v020/trials/sessions/C11_r1_dg_targeted/traces/20261111_124817_283039.json)|

[完整报告](../evaluation/final_acceptance/20261111_v020/summary.md)包含所有19次结果、分类、失败、变换是否触发、复现命令和最小下一步建议。X04文件顺序被排序抵消，不能作为位置鲁棒性成功；受控reverse实际反转并出现附带错误，完整保留。

当前候选源码哈希标识见[identity](../evaluation/final_acceptance/20261111_v020/candidate/identity.json)，不是只靠旧commit。实际总用时待候选人补充，未将运行耗时冒充个人投入。
