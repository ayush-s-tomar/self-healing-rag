"""
Assembles the self-healing RAG graph:

    retrieve -> generate -> critique --grounded--> mark_answered -> END
                               |
                               |--not grounded, retries left--> reformulate -> retrieve (loop)
                               |
                               |--not grounded, retries exhausted--> fallback -> END
"""

from langgraph.graph import StateGraph, END

from nodes import (
    RAGState,
    retrieve_node,
    generate_node,
    critique_node,
    reformulate_node,
    fallback_node,
    mark_answered,
    route_after_critique,
)


def build_graph():
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("critique", critique_node)
    graph.add_node("reformulate", reformulate_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("mark_answered", mark_answered)

    graph.set_entry_point("retrieve")

    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "critique")

    graph.add_conditional_edges(
        "critique",
        route_after_critique,
        {
            "accept": "mark_answered",
            "retry": "reformulate",
            "fallback": "fallback",
        },
    )

    graph.add_edge("reformulate", "retrieve")  # the self-healing loop
    graph.add_edge("mark_answered", END)
    graph.add_edge("fallback", END)

    return graph.compile()


# Compiled once at import time, reused across requests
rag_graph = build_graph()


def run_query(query: str) -> dict:
    """Run the graph end-to-end for a single query and return the final state."""
    initial_state = {
        "query": query,
        "active_query": query,
        "retry_count": 0,
        "trace": [],
    }
    final_state = rag_graph.invoke(initial_state)
    return final_state
