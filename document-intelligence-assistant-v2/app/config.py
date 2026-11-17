"""All settings in one place. Every value can be set with an environment variable
(locally in a .env file, on Render/Railway in the dashboard) so no secret lives in the code."""
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PDF_DIR = DATA_DIR / "pdfs"
CHROMA_DIR = DATA_DIR / "chroma"
LOG_FILE = Path(os.getenv("LOG_FILE", BASE_DIR / "logs" / "requests.jsonl"))

# --- Which AI service? "ollama" (local, free) or "openai" (any OpenAI-compatible hosted API) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")          # SECRET
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2" if LLM_PROVIDER == "ollama" else "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text" if LLM_PROVIDER == "ollama" else "text-embedding-3-small")
LLM_TEMPERATURE = os.getenv("LLM_TEMPERATURE", "0")       # set to empty to not send it

# --- Protect your API (and your wallet). If set, clients must send header  X-API-Key ---
API_KEY = os.getenv("API_KEY", "")                         # SECRET
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
AUTO_INGEST = os.getenv("AUTO_INGEST", "true").lower() == "true"  # ingest data/pdfs on startup if DB is empty

# --- Tuning knobs (change, re-run evals, compare) ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "1.0"))

# Example hosted prices (USD per 1M tokens) for the cost estimate. Check your provider's price list.
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "3.0"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "15.0"))

# A different embedding model gives different-size vectors, so each model gets its own collection.
COLLECTION_NAME = "docs_" + re.sub(r"[^a-zA-Z0-9]+", "_", EMBED_MODEL).strip("_")[:40]

NO_ANSWER = "I could not find this in the uploaded documents."

PDF_DIR.mkdir(parents=True, exist_ok=True)
