---
title: Self Healing RAG
emoji: 🔁
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Self-Healing RAG

A Retrieval-Augmented Generation pipeline that doesn't just retrieve-and-generate —
it critiques its own output and retries.

Upload a PDF in the sidebar, ask a question, and expand "Self-healing trace"
to watch the critic evaluate groundedness and trigger retries in real time.

Built with LangGraph (cyclical StateGraph), Groq (LLaMA 3.1 8B critic / 3.3 70B
generator), and Chroma for vector storage.

**Note:** this Space uses free CPU hardware, so PDF ingestion and the first
query may take 20-30 seconds while models warm up.