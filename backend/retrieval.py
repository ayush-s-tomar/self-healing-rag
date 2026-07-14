"""
Vector store setup + retrieval helpers.

Uses Chroma (local, persistent) + sentence-transformers for embeddings so
this runs with zero paid embedding API calls. Swap EMBEDDING_MODEL for an
API-based embedder later if you want higher quality.
"""

import os
import uuid
from typing import List, Dict

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_store")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "self_healing_rag")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=_embedder,
)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Simple sliding-window chunker over raw text (section-aware would be
    better long-term, but this keeps the demo self-contained)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def ingest_pdf(file_path: str, source_name: str) -> int:
    """Extract text from a PDF, chunk it, and add it to the vector store.
    Returns the number of chunks ingested."""
    reader = PdfReader(file_path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = chunk_text(full_text)

    if not chunks:
        return 0

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]

    _collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return len(chunks)


def retrieve(query: str, k: int = 4) -> List[Dict]:
    """Return top-k chunks with source metadata and similarity distance."""
    results = _collection.query(query_texts=[query], n_results=k)

    if not results["documents"] or not results["documents"][0]:
        return []

    out = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        out.append({"text": doc, "source": meta.get("source", "unknown"), "distance": dist})
    return out


def collection_is_empty() -> bool:
    return _collection.count() == 0


def reset_collection():
    """Wipe the collection — useful when testing with a fresh PDF."""
    global _collection
    _client.delete_collection(COLLECTION_NAME)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=_embedder
    )
