"""
LangGraph orchestration for the Zepto support assistant.

StateGraph with 3 nodes:
  classify_intent     -> classifies query as policy_question / general_question
  retrieve_and_answer  -> retrieval (always real) + generation (branches on MOCK_LLM)
  direct_answer        -> generation only, no retrieval (branches on MOCK_LLM)

A conditional edge from classify_intent routes to retrieve_and_answer or
direct_answer based on the classification.
"""
import os
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from ingest import query_top_k
from prompts import render_answer_prompt, render_direct_prompt

POLICY_KEYWORDS = [
    "delivery",
    "return",
    "refund",
    "membership",
    "tracking",
    "cancel",
    "gift card",
    "support hours",
]


def mock_llm_enabled() -> bool:
    """True (mock/graded baseline) unless MOCK_LLM is explicitly set to '0'."""
    return os.environ.get("MOCK_LLM", "1") != "0"


class AssistantState(TypedDict, total=False):
    query: str
    intent: str  # "policy_question" | "general_question"
    retrieved: list  # list of {"id", "text", "distance"}
    answer: str
    sources: list
    confidence: float


def classify_intent(state: AssistantState) -> AssistantState:
    query = state["query"]

    if mock_llm_enabled():
        # Mock mode (graded baseline): keyword heuristic, no LLM call.
        lowered = query.lower()
        intent = "policy_question" if any(kw in lowered for kw in POLICY_KEYWORDS) else "general_question"
    else:
        # Optional MOCK_LLM=0 extension: call the LLM to classify instead.
        intent = _llm_classify_intent(query)

    return {**state, "intent": intent}


def _llm_classify_intent(query: str) -> str:
    """Optional real-LLM classification path (only used when MOCK_LLM=0)."""
    from llm_client import call_llm  # local import: only needed for the optional path

    prompt = (
        "Classify the following customer question as exactly one word, either "
        "'policy_question' (about Zepto delivery, returns, membership, tracking, "
        "cancellation, damaged/missing items, gift cards, or support hours) or "
        "'general_question' (anything else). Respond with only that one word.\n\n"
        f"Question: {query}"
    )
    raw = call_llm(prompt).strip().lower()
    return "policy_question" if "policy" in raw else "general_question"


def retrieve_and_answer(state: AssistantState) -> AssistantState:
    query = state["query"]

    # Retrieval always runs for real in both modes (no API key/network needed).
    hits = query_top_k(query, k=3)
    sources = [h["id"] for h in hits]

    if mock_llm_enabled():
        # Mock mode (graded baseline): canned templated answer, no LLM call.
        top_chunk_snippet = hits[0]["text"][:200] if hits else ""
        answer = f"Based on the retrieved context: {top_chunk_snippet}"
        confidence = 1.0
    else:
        # Optional MOCK_LLM=0 extension: real LLM grounded in retrieved chunks.
        context = "\n\n".join(f"[{h['id']}] {h['text']}" for h in hits)
        prompt = render_answer_prompt(query=query, context=context)
        answer, sources, confidence = _call_llm_structured(prompt, fallback_sources=sources)

    return {**state, "retrieved": hits, "answer": answer, "sources": sources, "confidence": confidence}


def direct_answer(state: AssistantState) -> AssistantState:
    query = state["query"]

    if mock_llm_enabled():
        # Mock mode (graded baseline): fixed canned string, no LLM call.
        answer = "I can only answer questions about Zepto policies right now."
        confidence = 1.0
    else:
        # Optional MOCK_LLM=0 extension: prompt the LLM directly, no retrieval.
        prompt = render_direct_prompt(query=query)
        answer, _sources, confidence = _call_llm_structured(prompt, fallback_sources=[])

    return {**state, "answer": answer, "sources": [], "confidence": confidence}


def _call_llm_structured(prompt: str, fallback_sources: list, max_retries: int = 2):
    """Optional real-LLM path: call the LLM, validate its JSON output against
    the AskResponse schema, and retry with a corrective instruction up to
    `max_retries` additional times if validation fails."""
    from llm_client import call_llm
    from schemas import AskResponse

    last_error: Optional[str] = None
    current_prompt = prompt

    for attempt in range(max_retries + 1):
        raw = call_llm(current_prompt)
        try:
            parsed = json.loads(raw)
            validated = AskResponse(**parsed)
            return validated.answer, validated.sources or fallback_sources, validated.confidence
        except Exception as exc:  # noqa: BLE001 - broad on purpose, this is a validation retry loop
            last_error = str(exc)
            current_prompt = (
                f"{prompt}\n\nYour previous response was invalid JSON or failed schema "
                f"validation ({last_error}). Respond again with ONLY a valid JSON object "
                'matching {"answer": str, "sources": [str], "confidence": float 0-1}.'
            )

    return (
        f"[error] LLM response failed schema validation after {max_retries + 1} attempts: {last_error}",
        fallback_sources,
        0.0,
    )


def route_after_classify(state: AssistantState) -> str:
    return "retrieve_and_answer" if state["intent"] == "policy_question" else "direct_answer"


def build_graph():
    graph = StateGraph(AssistantState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", retrieve_and_answer)
    graph.add_node("direct_answer", direct_answer)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {"retrieve_and_answer": "retrieve_and_answer", "direct_answer": "direct_answer"},
    )
    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_assistant(query: str) -> dict:
    graph = get_graph()
    result = graph.invoke({"query": query})
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0),
    }


if __name__ == "__main__":
    for q in ["Is standard delivery free?", "What's the capital of France?"]:
        print(q, "->", run_assistant(q))
