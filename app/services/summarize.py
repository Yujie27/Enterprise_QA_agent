from app.config import settings

def build_extractive_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "没有检索到相关内容，请先构建索引或补充文档。"

    lines = [f"根据检索到的资料，问题“{question}”可从以下内容回答："]
    for i, c in enumerate(chunks[:3], start=1):
        text = c["text"].replace("\n", " ")
        if len(text) > 180:
            text = text[:180] + "..."
        lines.append(f"{i}. 来源《{c['source']}》：{text}")
    lines.append("以上为基于本地检索的抽取式回答；如配置 LLM，可生成更自然的总结。")
    return "\n".join(lines)

def try_llm_answer(question: str, chunks: list[dict]) -> str | None:
    if settings.llm_provider.lower() != "openai":
        return None
    if not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        context = "\n\n".join(
            [f"[{i+1}] 来源:{c['source']} chunk:{c['chunk_id']}\n{c['text']}" for i, c in enumerate(chunks)]
        )
        prompt = f"""你是研发文档与实验日志助手。请只基于给定资料回答问题，并尽量给出依据。

问题：
{question}

资料：
{context}

要求：
1. 不要编造资料外的信息。
2. 回答要简洁。
3. 最后列出引用来源文件名。
"""
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "你是严谨的研发文档问答助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"LLM 调用失败，已回退到抽取式回答。错误：{e}"

def answer_question(question: str, chunks: list[dict], use_llm: bool = False) -> str:
    if use_llm:
        llm_answer = try_llm_answer(question, chunks)
        if llm_answer:
            return llm_answer
    return build_extractive_answer(question, chunks)

def summarize_chunks(query: str, chunks: list[dict], use_llm: bool = False) -> str:
    if not chunks:
        return "没有检索到可总结的内容。"
    if use_llm:
        llm_answer = try_llm_answer(f"请总结以下内容中与“{query}”相关的主要问题和结论", chunks)
        if llm_answer:
            return llm_answer

    points = [f"围绕“{query}”，检索到 {len(chunks)} 条相关片段。"]
    for i, c in enumerate(chunks[:5], 1):
        text = c["text"].replace("\n", " ")
        points.append(f"{i}. {c['source']}：{text[:160]}{'...' if len(text) > 160 else ''}")
    return "\n".join(points)
