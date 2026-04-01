from __future__ import annotations

from pathlib import Path
from typing import Any, List, TypedDict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from langgraph.graph import StateGraph, START, END

from llama_index.core.llms import ChatMessage
from llama_index.llms.anthropic import Anthropic

from kardia.chat.chat_repository import get_chat_or_404, list_chat_messages

from kardia.config import Config
from kardia.retrieval.config import RetrievalConfig
from kardia.retrieval.service import RetrievalService
from kardia.chat.collapser import collapse_results
from kardia.retrieval.schemas import RetrievalResult

config = Config()

_chat_engine = create_engine(config.POSTGRES_URL, future=True)
ChatSessionLocal = sessionmaker(bind=_chat_engine, autoflush=False, autocommit=False, future=True)

retrieval_service = RetrievalService(RetrievalConfig())

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts" / "system-prompt.md"
LORE_SEED_PATH = PROJECT_ROOT / "prompts" / "lore-seed.md"

# Read the base system prompt at module load time.
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

class GraphState(TypedDict, total=False):
    chat_id: int
    user_query: str
    top_k: int
    retriever: str
    model: str
    temperature: float

    history: list[dict[str, str]]
    retrieved_context: list[dict[str, Any]]
    collapsed_context: list[dict[str, Any]]
    retrieved_prompt: str
    system_prompt: str
    answer: str

    max_tokens: int 

from kardia.retrieval.schemas import RetrievalResult
def load_history_node(state: GraphState) -> dict[str, Any]:
    chat_id = state["chat_id"]

    with ChatSessionLocal() as db:
        chat = get_chat_or_404(db, chat_id)
        if chat is None:
            raise ValueError(f"Chat {chat_id} not found.")

        messages = list_chat_messages(db, chat_id)
        history = [{"role": m.role, "content": m.content} for m in messages]

    return {"history": history}

def retrieve_context_node(state: GraphState) -> dict[str, List[RetrievalResult]]:
    user_query = state["user_query"]
    k = state.get("top_k", 5)
    retriever = state.get("retriever", "hybrid")

    retrieval_response = retrieval_service.retrieve(user_query, k=k, mode=retriever)
    # retrieved_context = [i.model_dump() for i in retrieval_response.results]
    return {"retrieved_context": retrieval_response.results}

def collapse_context_node(state: GraphState) -> dict[str, List[dict[str, Any]]]:
    retrieved_context = state["retrieved_context"]
    collapsed_context = collapse_results(retrieved_context)
    return {"collapsed_context": collapsed_context}

def build_context_prompt(user_query: str, results: list[dict[str, Any]]) -> str:
    """
    Builds a formatted context prompt string from a user query and a list of retrieval results.

    Args:
        user_query (str): The user's query to be appended at the end of the prompt.
        results (list[dict[str, Any]]): 
            A list of retrieval result objects, where each item is expected to support dictionary-style access for 'filename' and 'content' keys.

    Returns:
        str: A formatted string containing the retrieved context chunks and the user query.
    """
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

def build_context_prompt_node(state: GraphState) -> dict[str, str]:
    user_query = state["user_query"]
    retrieved_context = state["collapsed_context"]
    retrieved_context = [item.model_dump() for item in retrieved_context]

    retrieved_prompt  = build_context_prompt(user_query, retrieved_context)
    return {"retrieved_prompt": retrieved_prompt}

def add_lore_seed_to_prompt_node(state: GraphState) -> dict[str, str]:
    system_prompt = SYSTEM_PROMPT

    if LORE_SEED_PATH.exists():
        lore_seed = LORE_SEED_PATH.read_text(encoding="utf-8").strip()
        if lore_seed:
            system_prompt = (
                f"{SYSTEM_PROMPT.rstrip()}\n\n"
                "Campaign Lore Seed:\n"
                f"{lore_seed}"
            )

    return {"system_prompt": system_prompt}

def call_model_node(state: GraphState) -> dict[str, Any]:
    llm = Anthropic(
        model=state.get("model", config.LLM_MODEL),
        temperature=state.get("temperature", config.LLM_TEMPERATURE),
        max_tokens=state.get("max_tokens", 4000)
    )

    history = state.get("history", [])
    retrieved_prompt = state["retrieved_prompt"]
    system_prompt = state.get("system_prompt", SYSTEM_PROMPT)

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt)
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
    builder.add_node("collapse_context", collapse_context_node)
    builder.add_node("build_context_prompt", build_context_prompt_node)
    builder.add_node("add_lore_seed_to_prompt", add_lore_seed_to_prompt_node)
    builder.add_node("call_model", call_model_node)

    builder.add_edge(START, "load_history")
    builder.add_edge("load_history", "retrieve_context")
    builder.add_edge("retrieve_context", "collapse_context")
    builder.add_edge("collapse_context", "build_context_prompt")
    builder.add_edge("build_context_prompt", "add_lore_seed_to_prompt")
    builder.add_edge("add_lore_seed_to_prompt", "call_model")
    builder.add_edge("call_model", END)

    return builder.compile()
