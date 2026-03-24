# Kardia
A RAG-Pipeline for Homebrew Content Generation

## What is This?
Back in 2022, as ChatGPT and other LLMs began to show real-world prowess, I started experimenting with a early RAG pipeline for homebrew content generation. Called Yggdrasil, or Yggy for short, the idea was to make an AI Game Master. It was surprisingly not that hair brained of a scheme. You can find the code here `github.com/crossjbeer/yggdrasil`. 

When I built Yggy, I did so with the help of an AI pair programmer, but without the contemporary benefit of Langgraph or Llama-index or any other useful, now common tools. I watched these tools grow up around me and disheartendly expected my own ideas to be eaten by something larger like Google's Notebook LM or the like. However, a couple years further down the line, no such tool has emerged. While Dify or Notebook LM provide accessible RAG interfaces, nothing is so usable and configurable as I would like it to be, so here I am again. 

## How it Works: 

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

Once running, open `http://localhost:8080`

### Quick Stop
```bash
docker compose down 
```



You should start by cloning the repo: 
`git clone https://github.com/crossjbeer/kardia .`




