"""Ingest every PDF in data/pdfs/ (use after changing CHUNK_SIZE / CHUNK_OVERLAP).
Run from the project root:   python scripts/ingest_folder.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config          # noqa: E402
from app.ingest import ingest_pdf  # noqa: E402

pdfs = sorted(config.PDF_DIR.glob("*.pdf"))
if not pdfs:
    print(f"No PDFs found in {config.PDF_DIR}. Put your PDFs there first.")
for p in pdfs:
    print("Ingesting", p.name, "...", end=" ", flush=True)
    print(ingest_pdf(p))
print(f"\nDone. chunk_size={config.CHUNK_SIZE} overlap={config.CHUNK_OVERLAP}")
