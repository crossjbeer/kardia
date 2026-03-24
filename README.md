# Kardia
A RAG-Pipeline for Homebrew Content Generation

## What is This?
Back in 2022, as ChatGPT and other LLMs began to show real-world prowess, I started experimenting with an early RAG pipeline for homebrew content generation. Called Yggdrasil, or Yggy for short, the idea was to make an AI Game Master. It was surprisingly not that hair-brained of a scheme. You can find the code [here](https://github.com/crossjbeer/yggdrasil). 

When I built Yggy, I did so with the help of an AI pair programmer, but without the complementary benefits of Langgraph, Llama-index, or any other useful tools. I watched these tools grow up around me and disheartendly expected my own ideas to be eaten by something larger like Google's Notebook LM. You see that pessemism expressed on Yggy's short README. However, a couple years further down the line, no such tool has emerged. While Dify or Notebook LM provide accessible RAG interfaces, nothing is so usable and configurable as I would like it to be, so here I am again. Wahoo!

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

This opens our web interface where you can browse existing chats, make new chats, and view documents. 

### Quick Stop
```bash
docker compose down 
```

## How it Works: 
Kardia is (currently) a text-based RAG pipeline built in Docker using PostgreSQL, Langgraph, and Llama-Index. 

### Database 
Our project uses **PostgreSQL 16** with the **pgvector** extension for embedding-based semantic retrieval. Postgres is used here to demonstrate a production-adjacent environment. Simpler, light-weight solutions such as SQLite or an in-memory vector store are foregone to highlight scalability, indexing strategies, and integration with existing data infrastructure. 

#### Migrating
**Alembic** handles database migrations. Four version files exist: 
1. Register pgvector
2. Build tables
3. Create an embedding cosine similarity index 
4. Support keyword search 

#### Configuration: 
Four tables make up our database: 

**documents**: Stores metadata for each ingested file, including filename, file path, SHA-256 hash (for idempotent re-ingest), optional description, and creation timestamp. Each document can have multiple associated text chunks.

**chunks**: Represents segments of text from documents. Each chunk stores its content, start and end indices, and a vector embedding (dimension 384, matching bge-small). Chunks are linked to their parent document.

**chats**: Represents a conversation session, with a creation timestamp. Each chat can have multiple messages.

**chat_messages**: Stores individual messages within a chat, including the role ("user" or "assistant"), message content, and timestamp. Each message is linked to its parent chat.

### Ingestion
I leverage **Llama-index** to build an ETL pipe for **text** and **markdown** files. I utilize a **Strategy-pattern** to organize individual document ingestion strategies, and a **Registry** to serve them.  Documents are chunked into 512 character segments (the max supported by our embedding model), with a 64 character overlap. These settings can be configured in `kardia/ingest/config.py`.

This chunking style may prove limiting if we use keyword search more frequently. As of 2026-03-24, I am opting to keep the chunk size at 512 characters. 

#### Embeddings
I embed using the `BAAI/bge-small-en-v1.5` model served up through huggingface. This produces a dimension 384 vector representing each 512 character chunk produced from lore. 

`bge-small-en-v1.5` is chosen for its size (33.4M params, 133 mb) and ability to run locally. While embedding through most major companies is relatively inexpensive, this model is chosen to demonstrate the capabilities of small, OOTB solutions on abstract domains. More information on these BGE models is available [here](https://bge-model.com/tutorial/1_Embedding/1.2.1.html). 

Embedding accuracy can be improved with larger BERT-based models (bge-base, bge-large) or through privately mainted, GPT-derived models like text-embedding-003 or cohere's embed-v4. 

### Retrieval 
Retrieval is also handled via **Strategy-pattern** and **Registry**.

Support Retrieval Methods: 
1. Vector-based Top-k
2. Keyword-based Top-k

While **vector-based top-k** retrieval is often seen as optimal for RAG pipelines, **keyword-based** is typically overlooked. Keyword search can prove particularly useful in this niche domain where specific nouns and names are prevalent. A hybrid recommender is planned. 

### Chat
**Langgraph** handles our agentic chat approach. We build out a graph capable of loading chat history, retrieving context, and calling our LLM. **Langgraph** is chosen here for scalability and composability. 