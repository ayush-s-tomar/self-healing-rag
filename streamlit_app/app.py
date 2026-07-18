import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from retrieval import ingest_pdf, collection_is_empty, reset_collection  # noqa: E402
from graph import run_query  # noqa: E402

st.set_page_config(page_title="Self-Healing RAG", page_icon="🔁", layout="centered")

# ---------- Cosmetic: brand accent + button color + placeholder/footer styling ----------
st.markdown(
    """
    <style>
    :root {
        --accent: #6C5CE7;
        --accent-dark: #4A3F9E;
    }

    /* Title row with a small color chip for a "product" feel */
    .shr-title-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.1rem;
    }
    .shr-chip {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--accent), var(--accent-dark));
        flex-shrink: 0;
    }

    /* Primary buttons: brand indigo instead of default red.
       Different Streamlit versions expose this differently, so target all of them. */
    button[kind="primary"],
    button[data-testid="baseButton-primary"],
    .stButton > button[kind="primary"] {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
        color: white !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-dark) !important;
        border-color: var(--accent-dark) !important;
        color: white !important;
    }

    /* Idle-state placeholder card */
    .shr-placeholder {
        border: 1px dashed rgba(150, 140, 255, 0.35);
        border-radius: 10px;
        padding: 1.1rem 1.3rem;
        background: rgba(108, 92, 231, 0.06);
        margin-top: 0.6rem;
        margin-bottom: 1rem;
    }
    .shr-placeholder p {
        margin: 0;
        font-size: 0.92rem;
        opacity: 0.85;
    }

    /* Example question chips */
    .shr-chip-label {
        font-size: 0.8rem;
        opacity: 0.65;
        margin-bottom: 0.3rem;
    }

    /* Retry badges in trace */
    .shr-badge {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 9px;
        border-radius: 999px;
        background: var(--accent);
        color: white;
        margin-left: 8px;
        vertical-align: middle;
    }

    /* Footer */
    .shr-footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.08);
        font-size: 0.8rem;
        opacity: 0.55;
        text-align: center;
    }
    .shr-footer a {
        color: inherit;
        text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="shr-title-row"><span class="shr-chip"></span>'
    '<h1 style="margin:0;">Self-Healing RAG</h1></div>',
    unsafe_allow_html=True,
)
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
has_docs = not collection_is_empty()

# Default text input value, filled in by example chips below
if "shr_query" not in st.session_state:
    st.session_state.shr_query = ""

if not has_docs:
    st.markdown(
        '<div class="shr-placeholder"><p>👋 Upload a PDF in the sidebar, then ask a question — '
        'try something like <em>"What\'s covered under the warranty?"</em> to see a grounded answer, '
        'or ask about something the doc doesn\'t mention to watch the self-healing retry kick in.</p></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="shr-chip-label">Try one of these, or type your own below</div>', unsafe_allow_html=True)
    ex_cols = st.columns(3)
    example_questions = [
        "What does this document cover?",
        "Summarize the key numbers in this doc",
        "Is there anything about pricing or costs?",
    ]
    for col, ex in zip(ex_cols, example_questions):
        if col.button(ex, use_container_width=True):
            st.session_state.shr_query = ex

query = st.text_input("Ask a question about your uploaded document(s)", key="shr_query")

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

        with st.expander("🔍 Self-healing trace (see the critic at work)", expanded=True):
            retry_seen = 0
            for i, step in enumerate(trace, start=1):
                step_name = step.get("step", "unknown")
                is_retry = "retry" in step_name.lower() or "reformulat" in step_name.lower()
                badge = ""
                if is_retry:
                    retry_seen += 1
                    badge = f'<span class="shr-badge">Retry {retry_seen}</span>'
                st.markdown(f"**{i}. {step_name}**{badge}", unsafe_allow_html=True)
                st.json(step, expanded=False)

# ---------- Footer ----------
st.markdown(
    '<div class="shr-footer">Built with LangGraph + Groq + Chroma · '
    '<a href="https://github.com/ayush-s-tomar/self-healing-rag" target="_blank">View on GitHub</a></div>',
    unsafe_allow_html=True,
)