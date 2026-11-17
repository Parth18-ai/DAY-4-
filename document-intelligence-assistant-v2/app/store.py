"""ChromaDB collection (local folder data/chroma)."""
import chromadb

from . import config

_client = None


def get_collection():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _client.get_or_create_collection(config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
