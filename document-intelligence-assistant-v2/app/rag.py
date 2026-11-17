"""The question-answering pipeline: guard -> retrieve -> prompt -> LLM -> log."""
from . import config, llm
from .guard import SYSTEM_RULES, check_question, wrap_context
from .metrics import log_request, timer
from .store import get_collection


def retrieve(question: str, k: int) -> list:
    col = get_collection()
    n = col.count()
    if n == 0:
        return []
    q_vec = llm.embed([question])[0]
    res = col.query(query_embeddings=[q_vec], n_results=min(k, n))
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist <= config.MAX_DISTANCE:
            hits.append({"file": meta["file"], "page": meta["page"],
                         "text": doc, "distance": round(dist, 3)})
    return hits


def answer_question(question: str) -> dict:
    k = config.TOP_K

    # Layer 1: injection guard on the question
    ok, msg = check_question(question)
    if not ok:
        log_request(question, msg, "", 0, 0, 0, k, blocked=True)
        return {"answer": msg, "sources": [], "latency_s": 0.0, "blocked": True}

    with timer() as total:
        with timer() as t_ret:
            hits = retrieve(question, k)

        if not hits:  # nothing relevant found -> no need to call the LLM
            answer, prompt, p_tok, c_tok = config.NO_ANSWER, "", 0, 0
            t_gen = {"elapsed": 0.0}
        else:
            # Layers 2 + 3: sanitise chunks and mark them as data
            prompt = f"{wrap_context([h['text'] for h in hits])}\n\nQuestion: {question}"
            with timer() as t_gen:
                out = llm.chat(SYSTEM_RULES, prompt)
            answer, p_tok, c_tok = out["text"], out["prompt_tokens"], out["completion_tokens"]

    row = log_request(question, answer, prompt, total["elapsed"], t_ret["elapsed"],
                      t_gen["elapsed"], k, prompt_tokens=p_tok, completion_tokens=c_tok)
    return {"answer": answer,
            "sources": [{**h, "text": h["text"][:500]} for h in hits],
            "latency_s": row["latency_s"], "blocked": False,
            "prompt_tokens": row["prompt_tokens"], "completion_tokens": row["completion_tokens"]}
