import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Self-Healing RAG", page_icon="🔁", layout="centered")

st.title("🔁 Self-Healing RAG")
st.caption(
    "A RAG pipeline that critiques its own answers. If a response isn't "
    "grounded in the retrieved documents, it re-retrieves with a "
    "reformulated query instead of guessing."
)

# ---------- Sidebar: document management ----------
with st.sidebar:
    st.header("📄 Documents")

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Ingest PDF", type="primary"):
            with st.spinner("Chunking and embedding..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                resp = requests.post(f"{BACKEND_URL}/ingest", files=files)
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"Ingested {data['chunks_ingested']} chunks from {data['filename']}")
            else:
                st.error(resp.json().get("detail", "Ingestion failed."))

    st.divider()
    if st.button("🗑️ Reset knowledge base"):
        requests.post(f"{BACKEND_URL}/reset")
        st.success("Collection cleared.")

    st.divider()
    st.caption(
        "**Tip for demoing the self-healing loop:** ask a question that's "
        "only partially covered by your PDF, or phrased very differently "
        "from the document's wording — that's what tends to trigger a retry."
    )

# ---------- Main: query interface ----------
query = st.text_input("Ask a question about your uploaded document(s)")

if st.button("Ask", type="primary") and query:
    with st.spinner("Retrieving, generating, and self-checking..."):
        resp = requests.post(f"{BACKEND_URL}/query", json={"query": query})

    if resp.status_code != 200:
        st.error(resp.json().get("detail", "Query failed."))
    else:
        data = resp.json()

        # Status banner
        if data["final_status"] == "answered" and data["grounded"]:
            st.success("✅ Grounded answer" + (
                f" (after {data['retry_count']} retry)" if data["retry_count"] else ""
            ))
        else:
            st.warning("⚠️ Fell back — couldn't ground a confident answer")

        st.markdown("### Answer")
        st.write(data["answer"])

        if data["sources"]:
            st.caption("Sources: " + ", ".join(data["sources"]))

        # Reasoning trace — the whole point of this project
        with st.expander("🔍 Self-healing trace (see the critic at work)"):
            for i, step in enumerate(data["trace"], start=1):
                step_name = step.get("step", "unknown")
                st.markdown(f"**{i}. {step_name}**")
                st.json(step, expanded=False)
