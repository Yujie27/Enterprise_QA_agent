from app.services.ingest import build_index

if __name__ == "__main__":
    n = build_index()
    print(f"索引构建完成，共 {n} 个 chunk。")
