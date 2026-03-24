# Kardia
A RAG-Pipeline for Homebrew Content Generation

## What is This?
Back in 2022, as ChatGPT and other LLMs began to show real-world prowess, I started experimenting with an early RAG pipeline for homebrew content generation. Called Yggdrasil, or Yggy for short, the idea was to make an AI Game Master. It was surprisingly not that hair-brained of a scheme. You can find the code [here](https://github.com/crossjbeer/yggdrasil). 

When I built Yggy, I did so with the help of an AI pair programmer, but without the contemporary benefit of Langgraph or Llama-index or any other useful, now common tools. I watched these tools grow up around me and disheartendly expected my own ideas to be eaten by something larger like Google's Notebook LM or the like. You will see those feelings expressed on Yggy's short README. However, a couple years further down the line, no such tool has emerged. While Dify or Notebook LM provide accessible RAG interfaces, nothing is so usable and configurable as I would like it to be, so here I am again. Wahoo!

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
Kardia is (currently) a text-based RAG pipeline built in Docker with PostgreSQL, Langgraph, and Llama-Index. 

### Database 
Our project uses **PostgreSQL 16** with the **pgvector** extension for embedding-based semantic retrieval. Postgres is used here to demonstrate a production-adjacent environment. I have purposefully foregone using a potentially simpler, light-weight solution such as SQLite or an in-memory vector stores to highlight scalability, indexing strategies, concurrent access, and integration with existing data infrastructure. 

#### Migrating
**Alembic** handles database migrations. Three version files exist: 
1. Register pgvector
2. Build tables
3. Create an embedding cosine similarity index 

#### Configuration: 
Four tables make up our database: 

**documents** stores metadata for ingested files.
- filename
- file path 
- SHA-256 Hash (for idempotent re-ingestion)
- description (optional)
- creation timestamp 

**chunks** stores segments of text from documents. 
- content
- start index
- end index
- vector embedding (dim 384, matching bge-small)
__each chunk is linked to a parent document__

**chats** stores conversation sessions
- messages (links to the individual messages from a session)

**chat_messages** stores individual messages
- role (user/ assistant)
- content
- timestamp 
__messages are linked to the parent chat__


### Ingestion
We leverage **Llama-index** to ingest **text** and **markdown** files into our database. 