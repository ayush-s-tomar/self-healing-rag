import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from retrieval import ingest_pdf, collection_is_empty, reset_collection
from graph import run_query

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
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                try:
                    num_chunks = ingest_pdf(tmp_path, source_name=uploaded_file.name)
                finally:
                    os.remove(tmp_path)

            if num_chunks > 0:
                st.success(f"Ingested {num_chunks} chunks from {uploaded_file.name}")
            else:
                st.error("No extractable text found in this PDF (it may be scanned/image-based).")

    st.divider()
    if st.button("🗑️ Reset knowledge base"):
        reset_collection()
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
    if collection_is_empty():
        st.error("No documents have been ingested yet. Upload a PDF in the sidebar first.")
    else:
        with st.spinner("Retrieving, generating, and self-checking..."):
            final_state = run_query(query)

        grounded = final_state.get("grounded")
        final_status = final_state.get("final_status", "unknown")
        retry_count = final_state.get("retry_count", 0)
        answer = final_state.get("answer", "")
        trace = final_state.get("trace", [])
        sources = list({c["source"] for c in final_state.get("retrieved_chunks", [])})

        if final_status == "answered" and grounded:
            st.success("✅ Grounded answer" + (f" (after {retry_count} retry)" if retry_count else ""))
        else:
            st.warning("⚠️ Fell back — couldn't ground a confident answer")

        st.markdown("### Answer")
        st.write(answer)

        if sources:
            st.caption("Sources: " + ", ".join(sources))

        with st.expander("🔍 Self-healing trace (see the critic at work)"):
            for i, step in enumerate(trace, start=1):
                step_name = step.get("step", "unknown")
                st.markdown(f"**{i}. {step_name}**")
                st.json(step, expanded=False)
