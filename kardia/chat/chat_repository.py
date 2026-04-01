from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from kardia.db.models import Chat, ChatMessage


def create_chat(db: Session) -> Chat:
    chat = Chat()
    db.add(chat)
    db.flush()  # gets chat.id
    return chat


def get_chat_or_404(db: Session, chat_id: int) -> Chat | None:
    return db.get(Chat, chat_id)


def list_chat_messages(db: Session, chat_id: int) -> Sequence[ChatMessage]:
    chat = db.get(Chat, chat_id)
    if chat is None:
        return []
    return chat.messages


def append_message(
    db: Session,
    chat_id: int,
    role: str,
    content: str,
    retrieved_chunk_ids: list[int] | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        chat_id=chat_id,
        role=role,
        content=content,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )
    db.add(msg)
    db.flush()
    return msg