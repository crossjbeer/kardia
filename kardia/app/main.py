
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from anthropic import BadRequestError

from fastapi.middleware.cors import CORSMiddleware

from kardia.config import Config
from sqlalchemy.orm import sessionmaker, Session
from kardia.db.models import Document, Chunk
from kardia.retrieval.strategy_registry import retrieval_registry
from kardia.chat.schemas import SourceChunk as SourceChunkSchema


def _fetch_source_chunks(session: Session, chunk_ids: list[int]) -> list[SourceChunkSchema]:
    """Hydrate SourceChunk objects from the DB given a list of chunk IDs."""
    if not chunk_ids:
        return []
    rows = (
        session.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.id.in_(chunk_ids))
        .order_by(Chunk.id)
        .all()
    )
    return [
        SourceChunkSchema(
            chunk_ids=[chunk.id],
            document_id=chunk.document_id,
            filename=chunk.document.filename,
            filepath=chunk.document.filepath,
            description=chunk.document.description,
            content=chunk.content,
        )
        for chunk, doc in rows
    ]

database_url = Config.POSTGRES_URL

load_dotenv()
engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
PROMPTS_DIR = BASE_DIR.parent.parent / "prompts"
LORE_SEED_PATH = PROMPTS_DIR / "lore-seed.md"

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_ui():
    return FileResponse(TEMPLATES_DIR / "index.html")

@app.get("/documents-page")
def serve_documents():
    return FileResponse(TEMPLATES_DIR / "documents.html")

@app.get("/retrieval-playground")
def serve_retrieval_playground():
    return FileResponse(TEMPLATES_DIR / "retrieval-playground.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/tables")
def list_tables():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        result = {}
        for table in tables:
            result[table] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable"),
                    "default": str(col.get("default")) if col.get("default") is not None else None,
                }
                for col in inspector.get_columns(table)
            ]

        return result
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


###
# Documents
@app.get("/documents")
def list_documents():
    try:
        session = SessionLocal()
        docs = session.query(Document).all()
        result = []
        for doc in docs:
            chunk_count = session.query(Chunk).filter(Chunk.document_id == doc.id).count()
            result.append({
                "id": doc.id,
                "filename": doc.filename,
                "filepath": doc.filepath,
                "description": doc.description,
                "created_at": doc.created_at,
                "chunk_count": chunk_count
            })
        session.close()
        return result
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/documents/{document_id}")
def get_document(document_id: int):
    try:
        session = SessionLocal()
        doc = session.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        chunk_count = session.query(Chunk).filter(Chunk.document_id == doc.id).count()
        result = {
            "id": doc.id,
            "filename": doc.filename,
            "filepath": doc.filepath,
            "file_hash": doc.file_hash,
            "description": doc.description,
            "corpus": doc.corpus,
            "campaign": doc.campaign,
            "tags": doc.tags,
            "game_system": doc.game_system,
            "author": doc.author,
            "created_at": doc.created_at,
            "chunk_count": chunk_count,
        }
        session.close()
        return result
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


class DocumentUpdate(BaseModel):
    description: Optional[str] = None
    corpus: Optional[str] = None
    campaign: Optional[str] = None
    tags: Optional[str] = None
    game_system: Optional[str] = None
    author: Optional[str] = None


@app.put("/documents/{document_id}")
def update_document(document_id: int, body: DocumentUpdate):
    session = SessionLocal()
    try:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(doc, field, value)
        session.commit()
        session.refresh(doc)
        return {"id": doc.id, "filename": doc.filename}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


###
# Lore Seed
class LoreSeedUpdate(BaseModel):
    content: str

@app.get("/lore-seed")
def get_lore_seed():
    if LORE_SEED_PATH.exists():
        return {"content": LORE_SEED_PATH.read_text(encoding="utf-8"), "exists": True}
    return {"content": "", "exists": False}

@app.put("/lore-seed")
def update_lore_seed(body: LoreSeedUpdate):
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    LORE_SEED_PATH.write_text(body.content, encoding="utf-8")
    return {"status": "saved"}


### 
# Ingestion 
@app.post("/ingest")
def ingest():
    from kardia.ingest.service import IngestionService
    from kardia.ingest.config import IngestionConfig 
    
    #try:
    config = IngestionConfig()
    service = IngestionService(config)
    service.ingest_directory(Path(config.lore_dir))

    return {"status": "ingestion completed"}
    #except Exception as e:
    #    raise HTTPException(status_code=500, detail=str(e))
    

### 
# Chunks 
@app.get("/chunks/{document_id}")
def get_chunks_for_document(document_id: int):
    try:
        session = SessionLocal()
        chunks = session.query(Chunk).filter(Chunk.document_id == document_id).all()
        result = []
        for chunk in chunks:
            result.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "start_index": chunk.start_index,
                "end_index": chunk.end_index,
                # include the first 5 items in the embedding
                "embedding": ",".join(str(x) for x in chunk.embedding[:5]) if len(chunk.embedding) else None
            })
        session.close()
        return result
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

###
# Chat 
from kardia.chat.graph import build_graph
from kardia.chat.schemas import ChatRequest, ChatResponse
from kardia.db.models import Chat
from kardia.chat.chat_repository import create_chat, get_chat_or_404, append_message

chat_graph = build_graph()

@app.post("/chats")
def create_new_chat():
    session = SessionLocal()
    try:
        chat = create_chat(session)
        session.commit()
        session.refresh(chat)
        return {
            "chat_id": chat.id,
            "created_at": chat.created_at,
        }
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/chats")
def list_chats():
    session = SessionLocal()
    try:
        chats = session.query(Chat).order_by(Chat.created_at.desc()).all()
        return [
            {
                "chat_id": c.id,
                "created_at": c.created_at,
                "message_count": len(c.messages),
            }
            for c in chats
        ]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/chats/{chat_id}")
def get_chat_history(chat_id: int):
    session = SessionLocal()
    try:
        chat = get_chat_or_404(session, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        return {
            "chat_id": chat.id,
            "created_at": chat.created_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "retrieved_chunk_ids": m.retrieved_chunk_ids,
                    "retrieved_chunks": [
                        c.model_dump()
                        for c in _fetch_source_chunks(session, m.retrieved_chunk_ids or [])
                    ],
                    "created_at": m.created_at,
                }
                for m in chat.messages
            ],
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = SessionLocal()
    try:
        # Create or load selected chat
        if req.chat_id is None:
            chat = create_chat(session)
            session.commit()
            session.refresh(chat)
            chat_id = chat.id
        else:
            chat = get_chat_or_404(session, req.chat_id)
            if chat is None:
                raise HTTPException(status_code=404, detail=f"Chat {req.chat_id} not found")
            chat_id = chat.id

        # Save raw user message
        append_message(session, chat_id=chat_id, role="user", content=req.message)
        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        session.close()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

    # Run graph outside the DB write transaction
    try:
        result = chat_graph.invoke({
            "chat_id": chat_id,
            "user_query": req.message,
            "top_k": req.top_k,
            "model": req.model,
            "temperature": req.temperature,
        })

        answer = result.get("answer", "").strip()
        if not answer:
            raise HTTPException(status_code=500, detail="Model returned an empty answer.")

    except HTTPException:
        raise
    # catch a bad request from anthropic 
    except BadRequestError as e:
        message = str(e)

        if "usage limits" in message.lower():
            print(message.lower() )
            raise HTTPException(
                status_code=429,
                detail="Anthropic API usage limit reached. Try again later."
            )

        # fallback for other bad requests
        raise HTTPException(
            status_code=400,
            detail=message
        )
    
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

    # Flatten all chunk IDs from the collapsed context
    collapsed_context = result.get("collapsed_context", [])
    chunk_ids: list[int] = [
        cid
        for chunk in collapsed_context
        for cid in (chunk.chunk_ids or [])
    ]

    # Save assistant response
    session = SessionLocal()
    try:
        print(chunk_ids)
        append_message(
            session,
            chat_id=chat_id,
            role="assistant",
            content=answer,
            retrieved_chunk_ids=chunk_ids or None,
        )
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

    # Fetch persisted chunks from DB so the response reflects stored data
    session = SessionLocal()
    try:
        retrieved_chunks = _fetch_source_chunks(session, chunk_ids or [])
    finally:
        session.close()

    return ChatResponse(
        chat_id=chat_id,
        answer=answer,
        retrieved_chunks=retrieved_chunks,
    )

### 
# Retrieval 
@app.get("/retrieval-strategies")
def get_retrieval_strategies():
    # Return the list of registered retrieval strategies
    return {"strategies": list(retrieval_registry._strategies.keys())}


# Retrieval request model for JSON body
class RetrievalRequest(BaseModel):
    query: str
    strategy: str
    top_k: Optional[int] = 5

@app.post("/retrieve")
def retrieve(body: RetrievalRequest):
    session = SessionLocal()
    if not retrieval_registry.supports(body.strategy):
        raise HTTPException(status_code=400, detail=f"Strategy '{body.strategy}' not found")

    try:
        strategy = retrieval_registry.get(body.strategy)
        results = strategy.retrieve(session, body.query, k=body.top_k)

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()