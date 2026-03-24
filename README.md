# Kardia
A RAG-Pipeline for Homebrew Content Generation

## What is This?
Back in 2022, as ChatGPT and other LLMs began to show real-world prowess, I started experimenting with an early RAG pipeline for homebrew content generation. Called Yggdrasil, or Yggy for short, the idea was to make an AI Game Master. It was surprisingly not that hair-brained of a scheme. You can find the code [here](https://github.com/crossjbeer/yggdrasil). 

When I built Yggy, I did so with the help of an AI pair programmer, but without the contemporary benefit of Langgraph, Llama-index, or any other useful tools. I watched these tools grow up around me and disheartendly expected my own ideas to be eaten by something larger like Google's Notebook LM or the like. You see that pessemism expressed on Yggy's short README. However, a couple years further down the line, no such tool has emerged. While Dify or Notebook LM provide accessible RAG interfaces, nothing is so usable and configurable as I would like it to be, so here I am again. Wahoo!

## How to Use
Clone the repo and add your lore files (.txt, .md) to the folder called `lore`. Follow the tutorial below to produce a chat interface over your own files!

## Running 

### Docker
Docker Desktop is available for [Windows, Mac, and Linux](https://www.docker.com/products/docker-desktop/).

Alternatively, on Linux, you may use [Docker Engine](https://docs.docker.com/engine/install/) and the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/).

#### Checking your install
```bash
docker --version
docker compose version
```

### Quick Start
```bash
git clone https://github.com/crossjbeer/kardia
cd kardia
## **Add your lore files (.txt, .md) to the lore folder**
docker compose up --build
```

### Using
Once running, open `http://localhost:8080`

This opens our web interface where you can browse existing chats, make new chats, and evalaute retrieval context. 

### Quick Stop
```bash
docker compose down 
```

## How it Works: 
Kardia is (currently) a text-based RAG pipeline built in Docker using PostgreSQL, Langgraph, and Llama-Index. 

### Database 
Our project uses **PostgreSQL 16** with the **pgvector** extension for embedding-based semantic retrieval. Postgres is used here to demonstrate a production-adjacent environment. Simpler, light-weight solutions such as SQLite or an in-memory vector stores are foregone to highlight scalability, indexing strategies, and integration with existing data infrastructure. 

#### Migrating
**Alembic** handles database migrations. Three version files exist: 
1. Register pgvector
2. Build tables
3. Create an embedding cosine similarity index 

#### Configuration: 
Four tables make up our database: 

**documents**: Stores metadata for each ingested file, including filename, file path, SHA-256 hash (for idempotent re-ingest), optional description, and creation timestamp. Each document can have multiple associated text chunks.

**chunks**: Represents segments of text from documents. Each chunk stores its content, start and end indices, and a vector embedding (dimension 384, matching bge-small). Chunks are linked to their parent document.

**chats**: Represents a conversation session, with a creation timestamp. Each chat can have multiple messages.

**chat_messages**: Stores individual messages within a chat, including the role ("user" or "assistant"), message content, and timestamp. Each message is linked to its parent chat.

### Ingestion
I leverage **Llama-index** to build an ETL pipe for **text** and **markdown** files. I utilize a **Strategy-pattern** to organize individual document ingestion strategies, and a **Registry** to serve them.  Documents are chunked into 512 character segments (the max supported by our embedding model), with a 64 character overlap. These settings can be configured in `kardia/ingest/config.py`.

#### Embeddings
I embed using the `BAAI/bge-small-en-v1.5` model served up through huggingface. This produces a dimension 384 vector representing each 512 character chunk produced from lore. 

`bge-small-en-v1.5` is chosen for its size (33.4M params, 133 mb) and ability to run locally. While embedding through most major companies is relatively inexpensive, this model is chosen to demonstrate the capabilities of small, OOTB solutions on abstract domains. More information on these BGE models is available [here](https://bge-model.com/tutorial/1_Embedding/1.2.1.html). 

Embedding accuracy can be improved with larger BERT-based models (bge-base, bge-large) or through privately mainted, GPT-derived models like text-embedding-003 or cohere's embed-v4. 

### Retrieval 
