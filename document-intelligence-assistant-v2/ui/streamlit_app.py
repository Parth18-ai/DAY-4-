"""Streamlit UI.
Local:  streamlit run ui/streamlit_app.py
Config (secrets, never hard-coded):  API_URL and API_KEY
  - Streamlit Community Cloud: app Settings > Secrets (TOML)
  - Hugging Face Spaces: Settings > Secrets / Variables (they appear as environment variables)
  - Local: environment variables or ui/.streamlit/secrets.toml"""
import os

import requests
import streamlit as st


def _get(name, default=""):
    try:
        return str(st.secrets[name])
    except Exception:
        return os.getenv(name, default)


API_URL = _get("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = _get("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(page_title="Document Intelligence Assistant", page_icon="📄")
st.title("📄 Document Intelligence Assistant")


@st.cache_data(ttl=30, show_spinner="Contacting the API (free servers can take about a minute to wake up)...")
def fetch_status():
    try:
        h = requests.get(f"{API_URL}/health", timeout=90).json()
        m = requests.get(f"{API_URL}/metrics", headers=HEADERS, timeout=30)
        return h, (m.json() if m.ok else {})
    except Exception:
        return None, {}


def api_error(r):
    try:
        return r.json().get("detail", r.text)
    except Exception:
        return r.text


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Upload PDFs")
    files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    if st.button("Ingest", disabled=not files):
        for f in files:
            with st.spinner(f"Ingesting {f.name}..."):
                try:
                    r = requests.post(f"{API_URL}/ingest", headers=HEADERS,
                                      files={"file": (f.name, f.getvalue(), "application/pdf")}, timeout=600)
                    if r.ok:
                        d = r.json()
                        st.success(f"{f.name}: {d['pages']} pages, {d['chunks']} chunks")
                    else:
                        st.error(f"{f.name}: {api_error(r)}")
                except requests.exceptions.RequestException:
                    st.error("Cannot reach the API.")
        fetch_status.clear()

    st.divider()
    st.header("Status")
    h, m = fetch_status()
    if h is None:
        st.write("API: ❌ not reachable")
        st.caption(f"Trying: {API_URL}")
    else:
        st.write(f"API: ✅  |  LLM ({h['provider']}): {'✅' if h['llm_ready'] else '❌'}")
        st.caption(f"Chunks stored: {h['chunks_stored']} · top_k={h['settings']['top_k']} · "
                   f"chunk={h['settings']['chunk_size']}")
        if m.get("requests"):
            st.caption(f"Requests: {m['requests']} (blocked {m['blocked_by_guard']})")
            st.caption(f"Avg latency: {m['avg_latency_s']}s · p95: {m['p95_latency_s']}s")
            st.caption(f"Tokens: {m['total_tokens']} · est. cost if hosted: ${m['est_cost_usd_if_hosted']}")

# ---------------- Chat ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []


def show_sources(sources):
    with st.expander(f"Sources ({len(sources)})"):
        for i, s in enumerate(sources, 1):
            st.markdown(f"**{i}. {s['file']} — page {s['page']}**")
            st.caption(s["text"])


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            show_sources(msg["sources"])

if question := st.chat_input("Ask something about your documents"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        sources, foot = [], ""
        with st.spinner("Thinking..."):
            try:
                r = requests.post(f"{API_URL}/ask", json={"question": question}, headers=HEADERS, timeout=180)
                if r.ok:
                    data = r.json()
                    answer, sources = data["answer"], data["sources"]
                    foot = f"⏱ {data['latency_s']:.1f}s"
                else:
                    answer = f"⚠️ {api_error(r)}"
            except requests.exceptions.RequestException:
                answer = "⚠️ Cannot reach the API. If it is on a free plan it may be waking up. Try again in a minute."
        st.markdown(answer)
        if sources:
            show_sources(sources)
        if foot:
            st.caption(foot)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
