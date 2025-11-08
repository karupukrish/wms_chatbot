# WMS AI Chatbot (OpenRouter + MySQL + RAG)

## Overview
This project implements a dual-mode WMS chatbot:
- **TEXT (RAG)**: answers from uploaded PDFs using embeddings + FAISS
- **SQL (Live DB)**: generates SQL using an LLM and executes against MySQL

## Setup (Python 3.13)
1. Create a virtualenv and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` in project root (see `.env.template`):
   ```env
   OPENROUTER_API_KEY=sk-or-...
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=root
   DB_NAME=wms_db
   VECTOR_DIR=vectorstore.index
   DATA_DIR=data
   ```
4. Place PDFs in `data/` and restart the app (vectorstore will be built):
   ```bash
   uvicorn main:app --reload
   ```
5. Open `http://localhost:8000/docs` to test `/chat` endpoint.

## Notes
- This project uses OpenRouter via `openai.OpenAI` with a custom base_url.
- If you prefer OpenAI official API, update `config.py` and model IDs accordingly.
