from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from langgraph.graph import StateGraph, START, END

from llama_index.core.llms import ChatMessage
from llama_index.llms.anthropic import Anthropic

from .chat_repository import get_chat_or_404, list_chat_messages

from kardia.config import Config
from kardia.retrieval.config import RetrievalConfig
from kardia.retrieval.service import RetrievalService

config = Config()

_chat_engine = create_engine(config.POSTGRES_URL, future=True)
ChatSessionLocal = sessionmaker(bind=_chat_engine, autoflush=False, autocommit=False, future=True)

retrieval_service = RetrievalService(RetrievalConfig())

# read the system prompt from prompts/system-prompt.md at module load time
with open("prompts/system-prompt.md", "r") as f:
    SYSTEM_PROMPT = f.read()

class GraphState(TypedDict, total=False):
    chat_id: int
    user_query: str
    top_k: int
    model: str
    temperature: float

    history: list[dict[str, str]]
    retrieved_results: list[dict[str, Any]]
    retrieved_prompt: str
    answer: str


def build_retrieval_prompt(user_query: str, results: list[dict[str, Any]]) -> str:
    lines: list[str] = ["Retrieved Context:"]
    for i, item in enumerate(results, start=1):
        lines.extend(
            [
                f"Chunk {i}:",
                f"- name: {item['filename']}",
                f"- contents: {item['content'].strip()}",
                "",
            ]
        )
    lines.append(f"USER QUERY: {user_query}")
    return "\n".join(lines)


def load_history_node(state: GraphState) -> dict[str, Any]:
    chat_id = state["chat_id"]

    with ChatSessionLocal() as db:
        chat = get_chat_or_404(db, chat_id)
        if chat is None:
            raise ValueError(f"Chat {chat_id} not found.")

        messages = list_chat_messages(db, chat_id)
        history = [{"role": m.role, "content": m.content} for m in messages]

    return {"history": history}


def retrieve_context_node(state: GraphState) -> dict[str, Any]:
    user_query = state["user_query"]
    k = state.get("top_k", 5)

    retrieval_response = retrieval_service.retrieve(user_query, k=k)

    results = [r.model_dump() for r in retrieval_response.results]
    retrieved_prompt = build_retrieval_prompt(user_query, results)

    return {
        "retrieved_results": results,
        "retrieved_prompt": retrieved_prompt,
    }


def call_model_node(state: GraphState) -> dict[str, Any]:
    llm = Anthropic(
        model=state.get("model", config.LLM_MODEL),
        temperature=state.get("temperature", config.LLM_TEMPERATURE),
        max_tokens=6000,
    )

    history = state.get("history", [])
    retrieved_prompt = state["retrieved_prompt"]

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=SYSTEM_PROMPT)
    ]

    # prior DB chat history
    for msg in history:
        if msg["role"] not in ("user", "assistant"):
            continue
        messages.append(
            ChatMessage(role=msg["role"], content=msg["content"])
        )

    # latest turn sent in retrieval-augmented format
    messages.append(ChatMessage(role="user", content=retrieved_prompt))

    response = llm.chat(messages)
    answer = response.message.content if hasattr(response.message, "content") else str(response)

    return {"answer": answer}


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("load_history", load_history_node)
    builder.add_node("retrieve_context", retrieve_context_node)
    builder.add_node("call_model", call_model_node)

    builder.add_edge(START, "load_history")
    builder.add_edge("load_history", "retrieve_context")
    builder.add_edge("retrieve_context", "call_model")
    builder.add_edge("call_model", END)

    return builder.compile()
