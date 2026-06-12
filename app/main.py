from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    IngestResponse, AskRequest, AskResponse, Citation,
    SearchRequest, SearchResponse,
    ExperimentQueryRequest, ExperimentQueryResponse, ExperimentRecord,
    AgentRequest,
)
from app.services.ingest import build_index
from app.services.retrieve import search, ensure_index_ready
from app.services.summarize import answer_question, summarize_chunks
from app.services.experiment_query import query_experiments
from app.services.task_router import route_question

app = FastAPI(
    title="研发文档与实验日志智能助手",
    description="轻量 RAG/Agent Demo：文档问答、日志检索、实验查询、总结生成。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def to_citation(row: dict) -> Citation:
    return Citation(
        source=row.get("source", ""),
        doc_type=row.get("doc_type", ""),
        chunk_id=row.get("chunk_id", ""),
        score=float(row.get("score", 0.0)),
        text=row.get("text", ""),
    )

@app.get("/health")
def health():
    return {
        "status": "ok",
        "index_ready": ensure_index_ready(),
        "message": "研发文档与实验日志智能助手运行中",
    }

@app.post("/ingest", response_model=IngestResponse)
def ingest():
    n = build_index()
    return IngestResponse(ok=True, num_chunks=n, message=f"索引构建完成，共 {n} 个 chunk。")

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not ensure_index_ready():
        build_index()
    rows = search(req.question, top_k=req.top_k, doc_type=None)
    answer = answer_question(req.question, rows, use_llm=req.use_llm)
    return AskResponse(answer=answer, route="ask", citations=[to_citation(r) for r in rows])

@app.post("/search_logs", response_model=SearchResponse)
def search_logs(req: SearchRequest):
    if not ensure_index_ready():
        build_index()
    rows = search(req.query, top_k=req.top_k, doc_type="log")
    return SearchResponse(route="search_logs", matches=[to_citation(r) for r in rows])

@app.post("/search_docs", response_model=SearchResponse)
def search_docs(req: SearchRequest):
    if not ensure_index_ready():
        build_index()
    rows = search(req.query, top_k=req.top_k, doc_type="doc")
    return SearchResponse(route="search_docs", matches=[to_citation(r) for r in rows])

@app.post("/summarize", response_model=AskResponse)
def summarize(req: AskRequest):
    if not ensure_index_ready():
        build_index()
    rows = search(req.question, top_k=req.top_k, doc_type=None)
    answer = summarize_chunks(req.question, rows, use_llm=req.use_llm)
    return AskResponse(answer=answer, route="summarize", citations=[to_citation(r) for r in rows])

@app.post("/experiments", response_model=ExperimentQueryResponse)
def experiments(req: ExperimentQueryRequest):
    records, summary = query_experiments(req.query, top_k=req.top_k)
    return ExperimentQueryResponse(records=[ExperimentRecord(data=r) for r in records], summary=summary)

@app.post("/agent")
def agent(req: AgentRequest):
    if not ensure_index_ready():
        build_index()

    route = route_question(req.question)

    if route == "search_logs":
        rows = search(req.question, top_k=req.top_k, doc_type="log")
        return {"route": route, "answer": f"已按日志检索处理问题：{req.question}",
                "citations": [to_citation(r).model_dump() for r in rows]}

    if route == "summarize_logs":
        rows = search(req.question, top_k=req.top_k, doc_type="log")
        answer = summarize_chunks(req.question, rows, use_llm=req.use_llm)
        return {"route": route, "answer": answer, "citations": [to_citation(r).model_dump() for r in rows]}

    if route == "experiments":
        records, summary = query_experiments(req.question, top_k=req.top_k)
        return {"route": route, "answer": summary, "records": records}

    if route == "summarize_docs":
        rows = search(req.question, top_k=req.top_k, doc_type="doc")
        answer = summarize_chunks(req.question, rows, use_llm=req.use_llm)
        return {"route": route, "answer": answer, "citations": [to_citation(r).model_dump() for r in rows]}

    rows = search(req.question, top_k=req.top_k, doc_type=None)
    answer = answer_question(req.question, rows, use_llm=req.use_llm)
    return {"route": route, "answer": answer, "citations": [to_citation(r).model_dump() for r in rows]}
