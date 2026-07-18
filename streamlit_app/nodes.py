"""
Node functions for the self-healing RAG graph.

Each node takes the graph state (a dict / TypedDict) and returns a partial
state update, per LangGraph convention.
"""

import os
import json
import re
from typing import TypedDict, List, Dict, Optional

from langchain_groq import ChatGroq
from retrieval import retrieve as vector_retrieve

CRITIC_MODEL = os.getenv("CRITIC_MODEL", "llama-3.1-8b-instant")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

_generation_llm = ChatGroq(model=GENERATION_MODEL, temperature=0.2)
_critic_llm = ChatGroq(model=CRITIC_MODEL, temperature=0.0)


class RAGState(TypedDict, total=False):
    query: str                  # original user query
    active_query: str           # query currently used for retrieval (may be reformulated)
    retrieved_chunks: List[Dict]
    answer: str
    grounded: Optional[bool]
    critic_reason: str
    retry_count: int
    trace: List[Dict]           # human-readable log of what happened at each step, for UI display
    final_status: str           # "answered" | "fallback"


def retrieve_node(state: RAGState) -> RAGState:
    query = state.get("active_query") or state["query"]
    chunks = vector_retrieve(query, k=4)

    trace_entry = {
        "step": "retrieve",
        "query_used": query,
        "num_chunks": len(chunks),
    }

    return {
        "retrieved_chunks": chunks,
        "trace": state.get("trace", []) + [trace_entry],
    }


def generate_node(state: RAGState) -> RAGState:
    chunks = state.get("retrieved_chunks", [])
    context = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    ) or "No relevant context was found."

    # Use the active query (which may have been reformulated on a retry) so the
    # answer is generated against the same question that drove retrieval —
    # otherwise a retry fetches new chunks but re-answers the stale original
    # phrasing, defeating the point of reformulating in the first place.
    active_query = state.get("active_query") or state["query"]

    prompt = f"""Answer the question using ONLY the context below. If the context
does not contain enough information to answer confidently, say so explicitly —
do not guess or fill gaps with outside knowledge.

Context:
{context}

Question: {active_query}

Answer:"""

    response = _generation_llm.invoke(prompt)
    answer = response.content.strip()

    trace_entry = {"step": "generate", "answer_preview": answer[:200]}

    return {
        "answer": answer,
        "trace": state.get("trace", []) + [trace_entry],
    }


def critique_node(state: RAGState) -> RAGState:
    chunks = state.get("retrieved_chunks", [])
    context = "\n\n".join(c["text"] for c in chunks) or "No context was retrieved."

    prompt = f"""You are a strict fact-checking critic. Given the CONTEXT and the ANSWER,
determine if the answer is fully grounded in the context — i.e. every claim in
the answer can be traced back to something stated in the context.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"grounded": true or false, "reason": "one short sentence explaining why"}}

CONTEXT:
{context}

ANSWER:
{state['answer']}

JSON:"""

    response = _critic_llm.invoke(prompt)
    raw = response.content.strip()

    # Defensive parsing — strip markdown fences if the model adds them anyway
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        verdict = json.loads(raw)
        grounded = bool(verdict.get("grounded", False))
        reason = str(verdict.get("reason", "No reason provided."))
    except (json.JSONDecodeError, AttributeError):
        # If the critic fails to return valid JSON, fail safe: treat as
        # ungrounded so the loop retries rather than silently trusting it.
        grounded = False
        reason = f"Critic returned unparseable output: {raw[:150]}"

    trace_entry = {
        "step": "critique",
        "grounded": grounded,
        "reason": reason,
    }

    return {
        "grounded": grounded,
        "critic_reason": reason,
        "trace": state.get("trace", []) + [trace_entry],
    }


def reformulate_node(state: RAGState) -> RAGState:
    """Rewrite the query to try to pull back better chunks on retry."""
    prompt = f"""The following question was answered, but a fact-checker flagged the
answer as not well-grounded in the retrieved documents. Rewrite the question
to be more specific or use different phrasing/keywords, so retrieval pulls
back more relevant context. Return ONLY the rewritten question, nothing else.

Original question: {state['query']}
Why the previous attempt failed: {state.get('critic_reason', 'unknown')}

Rewritten question:"""

    response = _generation_llm.invoke(prompt)
    new_query = response.content.strip().strip('"')

    trace_entry = {
        "step": "reformulate",
        "new_query": new_query,
    }

    return {
        "active_query": new_query,
        "retry_count": state.get("retry_count", 0) + 1,
        "trace": state.get("trace", []) + [trace_entry],
    }


def fallback_node(state: RAGState) -> RAGState:
    """Reached when retries are exhausted and the answer still isn't grounded."""
    fallback_answer = (
        "I don't have enough reliably grounded information in the provided "
        "documents to answer this confidently. You may want to rephrase the "
        "question or provide additional source material."
    )

    trace_entry = {"step": "fallback", "reason": "Max retries exhausted without grounding."}

    return {
        "answer": fallback_answer,
        "final_status": "fallback",
        "trace": state.get("trace", []) + [trace_entry],
    }


def mark_answered(state: RAGState) -> RAGState:
    return {"final_status": "answered"}


def route_after_critique(state: RAGState) -> str:
    """Conditional edge: decide where to go after the critic weighs in."""
    if state.get("grounded"):
        return "accept"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "fallback"
    return "retry"