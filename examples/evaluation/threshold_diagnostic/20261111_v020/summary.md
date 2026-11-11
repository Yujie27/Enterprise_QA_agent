# 检索匹配门槛诊断实验

固定去重与来源呈现，仅在隔离加载的knowledge.py副本中把minimum_overlap改为1；原源码及默认行为未改。非空查询仍须有重合，评分排序及Top-k完全沿用。没有模型调用。

推荐运行仍为 `uv run --locked enterprise-qa --retrieval-mode dedup`；按需改写需显式添加`--demand-rewrite`。

|组|k|原Recall→放宽|完整覆盖原→放宽|新增候选标签统计|退化|
|---|---|---|---|---|---|
|frozen|1|76.00%→76.00%|13/25→13/25|{}|0|
|frozen|3|98.00%→100.00%|24/25→25/25|{'unreviewed': 3, 'direct_support': 1}|0|
|frozen|5|98.00%→100.00%|24/25→25/25|{'unreviewed': 3, 'direct_support': 1}|0|
|frozen|10|98.00%→100.00%|24/25→25/25|{'unreviewed': 3, 'direct_support': 1}|0|
|C11_trace|1|30.43%→30.43%|5/23→5/23|{'unreviewed': 6}|0|
|C11_trace|3|43.48%→100.00%|8/23→23/23|{'direct_support': 15, 'unreviewed': 10}|0|
|C11_trace|5|43.48%→100.00%|8/23→23/23|{'direct_support': 15, 'unreviewed': 10}|0|
|C11_trace|10|43.48%→100.00%|8/23→23/23|{'direct_support': 15, 'unreviewed': 10}|0|
|development|1|50.00%→50.00%|0/2→0/2|{}|0|
|development|3|75.00%→100.00%|1/2→2/2|{'direct_support': 1}|0|
|development|5|75.00%→100.00%|1/2→2/2|{'direct_support': 1}|0|
|development|10|75.00%→100.00%|1/2→2/2|{'direct_support': 1}|0|

必要证据按原始doc/section严格计算，R05探索性排除，R06不进入Recall分母；Trace按实际调用次数加权，重复查询保留。DEV01不用于比较。完整候选、分数、原文、元数据和新增候选见results.jsonl。

相关条款比例必须报告上下界：direct/equivalent/boundary/other_scope视为相关，unreviewed不能直接算无关；下界=已标相关/候选总数，上界=(已标相关+待复核)/候选总数。边界相关不等于可答。

original冻结k=5候选标签：{'direct_support': 36, 'unreviewed': 7, 'boundary_related': 1, 'related_other_scope': 1}，相关比例区间38/45—45/45。冲突子集完整：7/7（以列出的多证据冲突子集为准，非完整9题指标）。

one_overlap冻结k=5候选标签：{'direct_support': 37, 'unreviewed': 10, 'boundary_related': 1, 'related_other_scope': 1}，相关比例区间39/49—49/49。冲突子集完整：7/7（以列出的多证据冲突子集为准，非完整9题指标）。

结论：请结合逐条D04变化判断硬门槛作用；放宽可允许原先只有一个重叠词的材料候选进入，但不能保证语义支持或解决未知范围。未完成相关性人工复核的候选明确保留不确定性，本轮不能仅凭召回提升推荐替换默认；需进一步研究候选筛选。未增加BM25、向量、重排或回答校验。

复现：`.venv/Scripts/python.exe -B scripts/threshold_diagnostic.py --output examples/evaluation/threshold_diagnostic/replay_01`。独立目录排他创建。