import pandas as pd
from app.config import settings
from app.utils.file_loader import load_experiments_csv

def query_experiments(query: str = "", top_k: int = 5) -> tuple[list[dict], str]:
    df = load_experiments_csv(settings.experiments_path)
    if df.empty:
        return [], "未找到 experiments.csv 或文件为空。"

    q = query.lower().strip()
    result = df.copy()

    if "win" in q:
        col = "win_rate"
        if col in result.columns:
            result = result.sort_values(col, ascending=False)
            summary = f"按 {col} 从高到低返回前 {top_k} 条实验。"
        else:
            summary = "未找到 win_rate 字段，返回原始前几条。"
    elif "score" in q:
        col = "avg_score"
        if col in result.columns:
            result = result.sort_values(col, ascending=False)
            summary = f"按 {col} 从高到低返回前 {top_k} 条实验。"
        else:
            summary = "未找到 avg_score 字段，返回原始前几条。"
    elif q:
        mask = pd.Series([False] * len(result))
        for col in result.columns:
            mask = mask | result[col].astype(str).str.lower().str.contains(q, na=False)
        filtered = result[mask]
        if not filtered.empty:
            result = filtered
            summary = f"按关键词“{query}”筛选到 {len(result)} 条实验。"
        else:
            summary = f"未按关键词“{query}”筛选到实验，返回原始前几条。"
    else:
        summary = "未指定查询条件，返回原始前几条。"

    records = result.head(top_k).fillna("").to_dict(orient="records")
    return records, summary
