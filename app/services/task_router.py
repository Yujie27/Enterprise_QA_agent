def route_question(question: str) -> str:
    q = question.lower()
    log_keywords = ["日志", "log", "epoch", "loss", "win-rate", "win_rate", "avg_score",
                    "流局", "点炮", "seat", "bias", "耗时", "异常", "错误"]
    exp_keywords = ["实验", "run", "版本", "模型", "acc", "accuracy", "score",
                    "指标", "对比", "最好", "best"]
    summary_keywords = ["总结", "归纳", "原因", "分析", "复盘"]

    if any(k in q for k in log_keywords) and any(k in q for k in summary_keywords):
        return "summarize_logs"
    if any(k in q for k in log_keywords):
        return "search_logs"
    if any(k in q for k in exp_keywords):
        return "experiments"
    if any(k in q for k in summary_keywords):
        return "summarize_docs"
    return "ask"
