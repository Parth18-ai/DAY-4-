"""FastAPI backend.
Local:   uvicorn app.main:app --reload --port 8000
Routes:  GET /health (open) | POST /ingest, POST /ask, GET /metrics (need X-API-Key if API_KEY is set)"""
import hmac
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config, llm, metrics
from .ingest import ingest_pdf
from .rag import answer_question
from .store import get_collection


def _seed_database():
    """On startup, if the database is empty, ingest the PDFs shipped in data/pdfs."""
    try:
        if get_collection().count() == 0:
            for pdf in sorted(config.PDF_DIR.glob("*.pdf")):
                print("Seeding:", ingest_pdf(pdf), flush=True)
    except Exception as e:
        detail = getattr(getattr(e, "response", None), "text", "")[:400].replace("\n", " ")
        print("Seeding skipped:", repr(e), detail, flush=True)
        key = config.OPENAI_API_KEY
        print("KEY CHECK: length", len(key), "starts with", key[:4], flush=True)


@asynccontextmanager
async def lifespan(app):
    if config.AUTO_INGEST:
        threading.Thread(target=_seed_database, daemon=True).start()
    yield


app = FastAPI(title="Document Intelligence Assistant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])


def require_key(x_api_key: str = Header(default="")):
    """If API_KEY is configured, every protected route must send a matching X-API-Key header."""
    if config.API_KEY and not hmac.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(401, "Invalid or missing API key.")


def provider_error(e: Exception) -> HTTPException:
    """Turn an AI-service failure into a clear message (never includes secrets)."""
    if isinstance(e, requests.exceptions.ConnectionError):
        if config.LLM_PROVIDER == "ollama":
            return HTTPException(503, "Cannot reach Ollama. Start it with 'ollama serve' and pull the models: "
                                      f"ollama pull {config.CHAT_MODEL} && ollama pull {config.EMBED_MODEL}")
        return HTTPException(503, "Cannot reach the LLM provider.")
    status = getattr(getattr(e, "response", None), "status_code", None)
    if status in (401, 403):
        return HTTPException(502, "The LLM provider rejected the API key. Check OPENAI_API_KEY.")
    if status == 429:
        return HTTPException(502, "The LLM provider rate limit or quota was hit. Try again later.")
    return HTTPException(502, f"LLM provider error (HTTP {status}).")


class AskIn(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "provider": config.LLM_PROVIDER, "llm_ready": llm.llm_ready(),
            "chunks_stored": get_collection().count(),
            "chat_model": config.CHAT_MODEL, "embed_model": config.EMBED_MODEL,
            "auth_required": bool(config.API_KEY),
            "settings": {"chunk_size": config.CHUNK_SIZE, "overlap": config.CHUNK_OVERLAP,
                         "top_k": config.TOP_K}}


@app.post("/ingest", dependencies=[Depends(require_key)])
def ingest(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    data = file.file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large (max {config.MAX_UPLOAD_MB} MB).")
    dest = config.PDF_DIR / Path(file.filename).name
    dest.write_bytes(data)
    try:
        return ingest_pdf(dest)
    except requests.exceptions.RequestException as e:
        raise provider_error(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/ask", dependencies=[Depends(require_key)])
def ask(body: AskIn):
    try:
        return answer_question(body.question)
    except requests.exceptions.RequestException as e:
        raise provider_error(e)


@app.get("/metrics", dependencies=[Depends(require_key)])
def get_metrics():
    return metrics.summary()
