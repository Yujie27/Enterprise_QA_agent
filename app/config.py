from pathlib import Path
from pydantic import BaseModel
import os

class Settings(BaseModel):
    project_root: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = project_root.parent / "demo_data"
    docs_dir: Path = data_dir / "docs"
    logs_dir: Path = data_dir / "logs"
    experiments_path: Path = data_dir / "experiments.csv"
    index_dir: Path = project_root / "data_store" / "index"
    chunks_path: Path = index_dir / "chunks.jsonl"
    vectorizer_path: Path = index_dir / "tfidf_vectorizer.pkl"
    matrix_path: Path = index_dir / "tfidf_matrix.pkl"

    chunk_size: int = 500
    chunk_overlap: int = 100

    llm_provider: str = os.getenv("LLM_PROVIDER", "none")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

settings = Settings()
settings.index_dir.mkdir(parents=True, exist_ok=True)
