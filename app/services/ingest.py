import json
import pickle
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import settings
from app.utils.file_loader import load_text_files
from app.utils.text_cleaner import chunk_text

def build_chunks() -> list[dict]:
    raw_items = []
    raw_items.extend(load_text_files(settings.docs_dir, doc_type="doc"))
    raw_items.extend(load_text_files(settings.logs_dir, doc_type="log"))

    chunks: list[dict] = []
    for item in raw_items:
        pieces = chunk_text(
            item["text"],
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        for i, text in enumerate(pieces):
            chunk_id = f"{item['doc_type']}::{item['source']}::{i}"
            chunks.append({
                "chunk_id": chunk_id,
                "source": item["source"],
                "path": item["path"],
                "doc_type": item["doc_type"],
                "text": text,
            })
    return chunks

def save_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def build_index() -> int:
    chunks = build_chunks()
    save_jsonl(settings.chunks_path, chunks)

    corpus = [c["text"] for c in chunks]
    if corpus:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            max_features=50000,
        )
        matrix = vectorizer.fit_transform(corpus)
    else:
        vectorizer = TfidfVectorizer()
        matrix = None

    with settings.vectorizer_path.open("wb") as f:
        pickle.dump(vectorizer, f)
    with settings.matrix_path.open("wb") as f:
        pickle.dump(matrix, f)

    return len(chunks)

if __name__ == "__main__":
    n = build_index()
    print(f"Built index with {n} chunks.")
