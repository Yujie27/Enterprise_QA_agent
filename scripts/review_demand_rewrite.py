"""Persist this run's manual semantic review; never use as a new-run judge.

The notes below were written after reading all 45 answers and actual tool returns.
Coverage statistics are separate from these judgments. No judge model is invoked.
"""
import json
from coverage_experiment import OUT
import agent_baseline as base

rows = [json.loads(s) for s in (OUT / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
notes = {
    "R01_r1": "仅依据已见D01答费用发生后30日，列版本日期原文，注明scope未提供；单证据正常。",
    "R06_r1": "两次搜索仅见排除育儿补贴的D01，未套用普通报销期限，正确说明办法缺口。",
    "R07_r1": "实际见研发D01和销售D02的scope，按研发答返程15日；明确销售20日不适用。没有反事实控制，不能因果证明不依赖顺序。",
    "C01_r1": "双方原文可见并读取，列30/15日、未知范围和优先级，请求确认，未追加先按15日建议。",
    "C01_r2": "双方原文可见并读取，保留冲突与范围缺口，请求确认，未自行选择期限。",
    "C01_r3": "双方原文可见并读取，列出冲突与缺少适用依据，未追加无来源的执行期限。",
    "C02_r1": "唯一D01支持费用发生后30日，限定未注明适用范围，没有假定隐藏冲突而拒答。",
    "C05_r1": "取得并读取不同版本日期的双方，明确新日期不自动等于替代优先级，列冲突并请求依据。",
    "C12_r1": "同文档S1和S2都可见并读到，分别列30/15，不按条款位置裁决。scope相同的措辞应理解为未给出差异，不能视为已核实范围。",
    "M01_r1": "核对两轮conversation：首轮区分非差旅普通费用与研发差旅，第二轮继承部门/费用类型，用已见D02回答返程15日。",
    "E03_r1": "两次实际返回为空，没有看到D01；正确保留日历口径未知、请求业务语境，不建议自然日或工作日。安全业务通过，但必要入口证据覆盖退化。",
    "F01_r1": "两次真实工具错误路径均触发，说明工具失败而非制度不存在；没有引用未见条款或编造发生时间。",
}
details = {
    "pilot_C11": {
        "C11_r1": (True, "首次搜索已见D01/D04，后续搜索无新增、再读双方。最终30日与合规票据均有据；不必要搜索仍存在。"),
        "C11_r2": (True, "第四步聚焦改写才得到D04；已有充分片段仍请求第五次read(D04)，被拒。答案有据但执行incomplete，不能算正常完成。"),
        "C11_r3": (False, "D01可见，材料检索未恢复D04；安全部分回答30日、材料未知，目标未完整完成。"),
    },
    "B": {
        "C11_r1": (False, "期限D01首搜可见，材料两次改写未恢复D04，最终如实保留材料缺口；安全但不完整。"),
        "C11_r2": (True, "第二步费用报销表达取得D04，与D01合齐；随后仍读双方，答案30日与合规票据正确，无次日起算扩张。"),
        "C11_r3": (False, "首搜D01，读取后材料改写无新增；未恢复D04，未编造材料，完整业务不通过。"),
        "C13_r1": (False, "两次search均COPY0—4的15日，D01从未可见；最终限定资料答15日，未覆盖冲突双方。模型还自行扩展到差旅专项需求，未形成有效冲突补查。"),
        "C13_r2": (False, "首搜副本，read(COPY0)后追溯D02，只有15日原件；未获得D01/30日，因此业务冲突目标失败。没有把全库内容补给模型。"),
        "C13_r3": (False, "search副本后read(COPY0)，仅15日可见；没有取得30日，不属于看见冲突仍裁决。来源叙述仅说措辞相同，没有扩张所有副本的copied_from。"),
    },
    "dedup_rewrite": {
        "C11_r1": (False, "首搜期限，读D01后两次材料搜索无新增，未见D04；材料缺口如实保留，业务不完整。"),
        "C11_r2": (False, "首搜D01、材料检索无新增、read(D01)、再换发票单据凭证仍无D04；安全但不完整。"),
        "C11_r3": (True, "第二步费用报销查询取得D04；随后读双方，30日与合规票据正确，未扩充其他必交材料或计算口径。"),
        "C13_r1": (True, "首次去重search已见D01/30日、D02/15日和八份核验来源元数据；read双方后并列冲突请求确认，副本叙述有实际source_info。"),
        "C13_r2": (True, "首次双方完整，读取后请求确认，没有15日执行建议；COPY0—7来源关系由实际source_info支持。"),
        "C13_r3": (False, "双方原文可见、主结论正确且请求确认，但开头断言通用范围、后文称适用范围相同。实际scope均未提供，不能证明通用适用；严格依据约束不通过，召回完整不等于回答通过。"),
    },
    "dev_B": {
        "DEV01_r1": (True, "第三步改写取得培训申请资料，最终答10日前、主管确认函及结业测验记录，并明确培训报名与申请是否同环节未知；来源边界正确，但该开发题存在环节等价标注歧义。"),
        "DEV02_r1": (True, "第二步资格改写取得转正员工条款，完整回答资格及资产门户登记后前台领取；扩展查借阅期限册数并无必要，但未编造细则。"),
        "DEV03_r1": (True, "首次已得时限与资料，随后读两份；正确答发现故障7日内、序列号及截图，无来源扩张。"),
    },
    "dev_combo": {
        "DEV01_r1": (False, "仅期限可见，材料两次聚焦仍未取得申请条款；安全但不完整；另有报名/申请环节标注歧义。"),
        "DEV02_r1": (False, "仅取得流程文档，覆盖表仍明确缺借阅条件，却读该文档后结束，称适用对象全体员工并把流程算条件；未恢复资格原文，不能依据完整语料替模型补转正限制。"),
        "DEV03_r1": (True, "首次两片段足够，仅一次search后直接结束，正确回答7日及序列号截图；这是简单问题不机械read的实际路径。"),
    },
}
reviews = []
for row in rows:
    specific = details.get(row["config"], {}).get(row["run_id"])
    passed, note = specific if specific else (True, notes[row["run_id"]])
    unsupported = []
    minor = []
    if (row["config"], row["run_id"]) == ("dedup_rewrite", "C13_r3"):
        unsupported = ["两份现行制度的通用范围存在冲突", "由于适用范围相同"]
    if (row["config"], row["run_id"]) == ("dedup_rewrite", "C01_r1"):
        minor = ["D02引文省略起算短语中的‘费用’二字，逐字不精确；起算语义与来源一致，记录引用措辞瑕疵，不判成错误期限或错引来源。"]
    if row["case_id"] == "C12":
        minor += ["‘同一/相同范围’应改成‘未给出范围差异’；全文也明确范围缺失，未据此给出通用期限，列措辞风险。"]
    if (row["config"], row["run_id"]) == ("dev_combo", "DEV02_r1"):
        minor += ["全体员工确来自已见流程文档元数据，并非凭空数字；问题是把文档scope直接当完整资格，并在覆盖表已知缺条件时停止。"]
    labels = []
    if row["missing"]: labels.append("必要证据未召回，模型未恢复")
    if row["recovered_after_first"]: labels.append("首次未召回，但模型通过后续动作恢复")
    if unsupported: labels.append("主答案正确，但附带无依据断言")
    if row["budget_rejections"]: labels.append("预算不足")
    review = dict(config=row["config"], run_id=row["run_id"], strict_business_pass=passed,
                  completed_and_business_pass=passed and row["status"] == "completed",
                  safe_terminal_and_business_pass=passed and row["status"] in {"completed", "insufficient_evidence", "tool_error"},
                  reason=note, labels=labels, unsupported_assertions=unsupported,
                  citation_and_wording_findings=minor,
                  annotation_uncertainty="培训报名与培训申请是否同一环节未明确；从开发业务总指标中排除，仍报告其原始证据覆盖和实际输出" if row["case_id"] == "DEV01" else None,
                  trace=row["trace"], gap_keys=row["missing"])
    reviews.append(review)
base.write(OUT / "reviews.json", dict(method="助手逐条人工语义复核实际可见ToolResponse、最终答案及多轮conversation；不是自动裁判，需候选人复审", 
           criterion="沿用先行plan：主结论、必要问题完整性、引用支持、资料缺口及无无依据制度断言；执行状态另计；安全部分回答不算目标完整", reviews=reviews))
print("Saved", len(reviews), "manual reviews")
