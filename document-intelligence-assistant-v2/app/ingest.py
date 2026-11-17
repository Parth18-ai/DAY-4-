"""PDF -> pages -> chunks -> embeddings -> ChromaDB."""
from pathlib import Path

import fitz  # PyMuPDF

from . import config, llm
from .store import get_collection


def extract_pages(pdf_path) -> list:
    pages = []
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, 1):
            pages.append((i, page.get_text()))
    return pages


def chunk_text(text: str, size: int, overlap: int) -> list:
    text = " ".join(text.split())  # tidy whitespace
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):  # try to cut at a space, not mid-word
            cut = text.rfind(" ", start + size // 2, end)
            if cut != -1:
                end = cut
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def ingest_pdf(pdf_path) -> dict:
    pdf_path = Path(pdf_path)
    name = pdf_path.name
    ids, docs, metas = [], [], []
    pages = extract_pages(pdf_path)
    for page_no, text in pages:
        for j, chunk in enumerate(chunk_text(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)):
            ids.append(f"{name}-p{page_no}-c{j}")
            docs.append(chunk)
            metas.append({"file": name, "page": page_no})
    if not docs:
        raise ValueError(f"No text found in {name}. It may be a scanned PDF (needs OCR).")

    col = get_collection()
    col.delete(where={"file": name})  # re-ingesting the same file replaces old chunks
    col.add(ids=ids, documents=docs, embeddings=llm.embed(docs), metadatas=metas)
    return {"status": "ok", "file": name, "pages": len(pages), "chunks": len(docs)}
