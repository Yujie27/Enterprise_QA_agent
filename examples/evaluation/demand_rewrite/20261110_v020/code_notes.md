# 实现、配置选择与复现

本轮只有三个业务文件变化，已测源码将保存在evaluated_source，原去重版本完整封存在sealed_a_dedup。

- knowledge.py增加deduplicate开关，关闭时直接沿用原匹配候选、原排序及Top-k。默认仍开启既有去重；没有修改同义词、匹配门槛、分数、source_info或去重规则。
- agent.py保留原SYSTEM_PROMPT及关闭时的原工具schema。开启时附加证据覆盖策略，增加可选coverage公开参数，模型自行识别需求、关联已见引用、决定缺口查询和结束。程序不生成问题拆解、不硬编码case、不注入gold、不验证答案或新增主动冲突补查。程序只统计实际(doc_id, section_id, text)新颖度、查询是否重复、每次底层查询数。每次search只有一次KnowledgeBase.search；read单独计预算。覆盖表是模型自述，有失真/滞后的实际记录，不能当作程序已证实的覆盖真值。
- cli.py提供两个正交开关，支持单轮及interactive；在Trace记录experiment_config。每轮工具4次，max_iters=5保持原样。

明确选择配置，无需切换工作区文件：

```powershell
# A：原版检索、原提示词/工具schema
uv run --locked enterprise-qa --retrieval-mode original "报销期限多久？"
# A＋去重与来源呈现
uv run --locked enterprise-qa --retrieval-mode dedup "报销期限多久？"
# B = A＋按需改写
uv run --locked enterprise-qa --retrieval-mode original --demand-rewrite "报销期限和所需材料是什么？"
# 去重＋按需改写
uv run --locked enterprise-qa --retrieval-mode dedup --demand-rewrite "报销期限和所需材料是什么？"
```

上述示例默认资料是data/policies.json，**不能**拿它替代C11指定语料。需要时显式传--corpus。关掉按需改写时不传该flag即可。离线mock只验证既有流程，不支持据其声明覆盖策略的真实效果。

本次实际命令（按先测、主测、重复、开发顺序；目录先行固定；真实模型使用本地.env，命令中不含密钥）：

```powershell
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py seal
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts/prepare_coverage_sets.py
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/pilot_C11 --mode original --batch pilot
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/B --mode original --batch primary
# 当时的4条模型前拒绝记录原样保存，恢复README后仅补尚未执行的4条：
.\.venv\Scripts\python.exe -B scripts/prepare_coverage_recovery.py
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/B_launcher_recovery --mode original --batch recovery
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/B --mode original --batch repeats
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/dedup_rewrite --mode dedup --batch primary
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/dedup_rewrite --mode dedup --batch repeats
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/dev_B --mode original --batch development
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder examples/evaluation/demand_rewrite/20261110_v020/dev_combo --mode dedup --batch development
.\.venv\Scripts\python.exe -B scripts/analyze_demand_rewrite.py
.\.venv\Scripts\python.exe -B scripts/review_demand_rewrite.py
.\.venv\Scripts\python.exe -B scripts/report_demand_rewrite.py
```

seal/prepare/采集/报告输出使用排他创建，原目录已存在时拒绝覆盖。上面的命令是执行记录，不要对已有目录重跑。最后两个脚本含本次人工判定及叙述，**不得当作新结果的自动裁判**。

完整重跑45次的新目录命令如下。不会覆盖封存结果；先确认本地模型可用。采用同一个已测版本，不要在运行期间编辑src、README、data、依赖或原基线。所有真实模型结果均保存，不自动重试业务失败。单进程watchdog900秒，最多2个独立会话并发，与4次工具预算独立。

```powershell
$trialRoot = 'examples/evaluation/demand_rewrite/replay_01'
.\.venv\Scripts\python.exe -B scripts/prepare_coverage_sets.py --root $trialRoot
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/pilot_C11" --mode original --batch pilot
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/B" --mode original --batch primary
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/B" --mode original --batch repeats
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/dedup_rewrite" --mode dedup --batch primary
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/dedup_rewrite" --mode dedup --batch repeats
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/dev_B" --mode original --batch development
.\.venv\Scripts\python.exe -B scripts/coverage_experiment.py run --folder "$trialRoot/dev_combo" --mode dedup --batch development
.\.venv\Scripts\python.exe -B scripts/analyze_demand_rewrite.py --root $trialRoot
# 阅读新observations.jsonl、完整ToolResponse、Trace及conversation，独立写新reviews与summary。
# 不调用review_demand_rewrite.py/report_demand_rewrite.py给新试验套用本次人工判定。
```

运行器仍调用真实cli.main、真实Agent、真实search_docs/read_doc；Agent.reply/_tool_response观察器原样返回对象，只记录公开输出、实际payload及usage，不记录私有推理。coverage公开参数由模型生成，程序统计另有source标识。每次资料都由计划指定corpus，普通会话隔离，M01通过原interactive入口共享会话。gold仅供离线复核，未进入模型提示或工具返回。

prepare_coverage_sets.py与analyze_demand_rewrite.py在运行完成后增加了--root，以便新目录复现；业务源码及实际执行的coverage_experiment.py/agent_baseline.py未因此改变。报告脚本只做采集、统计、归档，未调用模型或重选结果。
