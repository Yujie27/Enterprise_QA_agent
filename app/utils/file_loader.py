from pathlib import Path
import pandas as pd

TEXT_SUFFIXES = {".txt", ".md", ".log", ".yaml", ".yml", ".json"}

def read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")

def load_text_files(base_dir: Path, doc_type: str) -> list[dict]:
    items = []
    if not base_dir.exists():
        return items
    for path in sorted(base_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            items.append({
                "source": path.name,
                "path": str(path),
                "doc_type": doc_type,
                "text": read_text_file(path),
            })
    return items

def load_experiments_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)
