# Document Intelligence Assistant (v2)

Upload PDFs, ask questions, get answers with sources. Runs fully local (Ollama + ChromaDB).
UI: Streamlit. Backend: FastAPI. Includes prompt-injection guard, cost/latency logging and an eval runner.

## One-time setup
```
pip install -r requirements.txt -r ui/requirements.txt
ollama pull llama3.2
ollama pull nomic-embed-text
```

## Run (3 terminals, all from this project folder)
1. Backend:  `uvicorn app.main:app --reload --port 8000`   (check http://localhost:8000/docs)
2. UI:       `streamlit run ui/streamlit_app.py`
3. Evals:    `python evals/run_evals.py`

## Deploy
See DEPLOY.md: Docker, Render/Railway (API), Streamlit Community Cloud (UI), and `scripts/smoke_test.py` for live-URL checks.

## Folder guide
- app/main.py       API routes: /health /ingest /ask /metrics
- app/rag.py        guard -> retrieve -> prompt -> LLM -> log
- app/ingest.py     PDF -> chunks -> embeddings -> ChromaDB
- app/guard.py      prompt-injection protection
- app/metrics.py    cost + latency logging (logs/requests.jsonl)
- app/config.py     tuning knobs: CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, MAX_DISTANCE
- ui/streamlit_app.py   the Streamlit UI (own requirements in ui/requirements.txt)
- Dockerfile, docker-compose.yml, render.yaml, railway.json   deployment
- scripts/smoke_test.py   checks a running API (local or live)
- evals/            evals.json (edit it!) + run_evals.py
- scripts/ingest_folder.py   re-ingest all PDFs in data/pdfs after changing chunk settings

## Tuning loop
1. `python evals/run_evals.py` -> note AVERAGE SCORE and the WEAKEST 5.
2. Change ONE setting in .env (copy .env.example to .env), e.g. TOP_K=6 or CHUNK_SIZE=1000.
3. If you changed CHUNK_SIZE or CHUNK_OVERLAP: `python scripts/ingest_folder.py`.
4. Restart uvicorn, run the evals again, keep the change only if the score goes up.

## Sample data included
`data/pdfs/` has 3 sample policy PDFs (Northwind Technologies, fictional) and `evals/evals.json` has 20 matching
questions (17 answerable, 2 out-of-scope, 1 prompt-injection attack). The IT Security PDF also contains a hidden
fake "ignore all previous instructions" line to test the guard. To use your own PDFs, replace the files in
`data/pdfs/` and rewrite `evals/evals.json`.
