# Self-Healing RAG

A Retrieval-Augmented Generation pipeline that doesn't just retrieve-and-generate —
it critiques its own output and retries.

```
retrieve -> generate -> critique --grounded--> answer
                            |
                            |--not grounded, retries left--> reformulate -> retrieve (loop)
                            |
                            |--retries exhausted--> honest fallback ("I don't know")
```

Built with LangGraph (cyclical StateGraph), Groq (LLaMA 3.1 8B for the critic,
3.3 70B for generation), and Chroma for local vector storage.

## Project structure

```
self-healing-rag/
├── backend/
│   ├── main.py          # FastAPI app (upload PDF, ask questions)
│   ├── graph.py          # LangGraph wiring — the self-healing loop
│   ├── nodes.py           # retrieve / generate / critique / reformulate / fallback
│   ├── retrieval.py       # Chroma vector store + PDF chunking
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app.py            # Streamlit UI
    └── requirements.txt
```

## 1. Local setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

Edit `.env` and add your free Groq API key from https://console.groq.com/keys.

```bash
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000/health to confirm it's running.

### Frontend

In a second terminal:

```bash
cd frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

This opens the UI at http://localhost:8501. It talks to the backend at
`http://localhost:8000` by default — override with the `BACKEND_URL` env var
if needed.

## 2. Demoing the self-healing loop

1. Upload any PDF (a resume, a report, docs — anything with real text, not a
   scanned image) via the sidebar.
2. Ask a question that's clearly answerable from the doc — you should see
   `✅ Grounded answer`.
3. To **trigger the self-healing loop on camera**, ask something that's only
   loosely related to the document, or phrase it very differently from the
   document's own wording (e.g. ask about a topic adjacent to but not
   actually covered in the PDF). Expand "🔍 Self-healing trace" to show the
   critic flagging it, the reformulated query, and the retry.
4. Ask something totally unrelated to the PDF to trigger the **fallback**
   path — confirm it says "I don't have enough information" instead of
   hallucinating.

## 3. Deploying (Render)

**Backend:**
- New Web Service on Render, root directory `backend/`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add `GROQ_API_KEY` (and other `.env` vars) under Environment
- Note: Chroma's `PersistentClient` writes to local disk — on Render's free
  tier this resets on redeploy/restart. Fine for a demo; for persistence
  across restarts, add a Render Disk or swap to a hosted vector DB later.

**Frontend:**
- Deploy `frontend/` the same way you deployed your Agentic RAG Assistant's
  Streamlit app (Streamlit Community Cloud or Render)
- Set `BACKEND_URL` to your deployed backend's URL

## 4. Known limitations (v1, by design — see the build plan for what's cut)

- Chunking is a simple sliding window, not section-aware (unlike your
  AskMyDocs project's chunking logic — worth porting over later)
- Single-collection, single "knowledge base" at a time (no multi-tenant
  document sets)
- Query reformulation is a single LLM rewrite, not a sophisticated
  query-expansion strategy
- No auth — add a simple API key check before making this public
