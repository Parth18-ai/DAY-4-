# Deploy guide: API on Render (or Railway), UI on Streamlit Community Cloud

## The big picture
```
 You (browser) -> Streamlit UI (Streamlit Cloud) -> API (Render/Railway, Docker) -> hosted LLM (OpenAI-compatible)
```
**Important:** Render and Railway cannot run Ollama (too little memory). So the deployed API uses a *hosted* AI service
(`LLM_PROVIDER=openai`). Locally you can keep using Ollama. Same code, different environment variables.

## Secrets: what they are and where they live
| Secret | What it does | Where you set it |
|---|---|---|
| `OPENAI_API_KEY` | pays for the AI calls | Render/Railway dashboard (never in git) |
| `API_KEY` | password for your API; the UI and tests send it as header `X-API-Key` | Render generates it; copy it into Streamlit secrets |
| `API_URL` | address of your API | Streamlit secrets |

Rules: never commit `.env`; never paste a key in chat, screenshots or code. If one leaks, create a new key and delete the old one.
Without `API_KEY`, anyone who finds your URL can spend your OpenAI credit, so always set it.

## Step 0: Run it in Docker on your PC first
1. Install Docker Desktop. Copy `.env.example` to `.env` (Ollama settings are fine for local).
2. `docker compose up --build`
3. Open http://localhost:8000/docs and http://localhost:8000/health
4. `python scripts/smoke_test.py http://localhost:8000`
(Docker on Windows reaches your Ollama through `host.docker.internal`; already set in docker-compose.yml.
No Ollama? `docker compose --profile local-llm up --build`, put `OLLAMA_URL=http://ollama:11434` in `.env`, then
`docker compose exec ollama ollama pull llama3.2` and `... pull nomic-embed-text`.)

## Step 1: Push to GitHub
Push the whole project. Check `.env` is NOT in the repo. `data/pdfs/` (your sample PDFs) must be in the repo, the API ingests them on startup.

## Step 2A: Deploy the API on Render
1. Get an API key from your AI provider (e.g. OpenAI). Models in `render.yaml` are examples; check your provider's current model names.
2. render.com > New > **Blueprint** > connect the GitHub repo. Render reads `render.yaml`.
3. When asked, paste `OPENAI_API_KEY`. `API_KEY` is generated automatically.
4. Wait for the build (several minutes). Your URL looks like `https://doc-intel-api.onrender.com`.
5. Dashboard > your service > Environment: copy the generated `API_KEY`.
6. Open `<your-url>/health`. You should see `"status":"ok"`.

Free plan facts (Render docs, 2026): 512 MB RAM, 0.1 CPU; the service sleeps after 15 min without traffic and takes about a minute to wake;
the disk is wiped on every restart/redeploy. So uploaded PDFs disappear after a restart, but the PDFs in `data/pdfs/` are re-ingested automatically on startup.
If the build or runtime runs out of memory, move that service to the paid Starter plan (about $7/month).

## Step 2B (alternative): Railway
1. railway.com > New Project > Deploy from GitHub repo. It finds the `Dockerfile` (and `railway.json`).
2. Variables tab: add `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `CHAT_MODEL`, `EMBED_MODEL`, and `API_KEY` (make up a long random string).
3. Settings > Networking > **Generate Domain**. Open `<domain>/health`.

## Step 3: Deploy the UI on Streamlit Community Cloud
1. share.streamlit.io > Create app > pick your GitHub repo, branch `main`.
2. **Main file path:** `ui/streamlit_app.py` (dependencies come from `ui/requirements.txt`).
3. Advanced settings > **Secrets**, paste:
```
API_URL = "https://doc-intel-api.onrender.com"
API_KEY = "paste the API_KEY from Render"
```
4. Deploy. The first load can take about a minute while the free API wakes up.

Hugging Face Spaces alternative: create a Space for the Streamlit app, upload `ui/streamlit_app.py` and `ui/requirements.txt`, and add `API_URL` and `API_KEY`
under Settings > Secrets (the app reads them as environment variables). Check which Space type your account offers for Streamlit.

## Step 4: Smoke tests on the live URL
```
python scripts/smoke_test.py https://doc-intel-api.onrender.com --api-key YOUR_API_KEY
```
It waits for the server to wake up, then runs 10 checks: health, LLM configured, documents loaded, requests without a key are rejected (401),
a real question is answered with the right source and within the latency limit, prompt injection is blocked, an out-of-scope question is refused,
and the request shows up in `/metrics`. Exit code 0 = all passed. Save the printed output as proof for your submission.
Also open the Streamlit URL, ask a question and take a screenshot showing the answer and Sources.

You can also run your evals against the live API:
```
set API_URL=https://doc-intel-api.onrender.com   (Windows CMD; PowerShell: $env:API_URL="...")
set API_KEY=YOUR_API_KEY
python evals/run_evals.py --tag live
```

## Troubleshooting
| Problem | Fix |
|---|---|
| UI says API not reachable | The free API is waking up. Wait a minute and refresh. Check `API_URL` has no trailing path. |
| 401 from API | `API_KEY` in Streamlit secrets differs from the one on Render |
| 502 "provider rejected the API key" | `OPENAI_API_KEY` wrong or has no credit |
| 502 provider error on chat | Model name not available for your account, or provider rejects `temperature`: set `LLM_TEMPERATURE=` (empty) |
| `chunks_stored` is 0 | Startup ingestion failed (check Render logs); upload a PDF in the UI |
| Build fails or service restarts | Out of memory on the 512 MB free plan: upgrade to Starter |
| Switched embedding model | Each embedding model gets its own collection, so PDFs are re-ingested automatically on the next startup |
