# Local AI Knowledge Assistant

A locally hosted AI-powered document question-answering application built using **Retrieval-Augmented Generation (RAG)**. Upload PDF documents, retrieve relevant information, and ask questions through a conversational interface — using locally running language models.

The application combines **Ollama, ChromaDB, FastAPI, Python, SQLite, and React** to provide a private document intelligence workspace.

## Features

- **PDF Upload and Processing:** Upload PDF documents and extract their text.
- **Document Chunking:** Split extracted text into smaller chunks for efficient retrieval.
- **Vector Embeddings:** Generate document and query embeddings using Nomic embeddings.
- **Semantic Search:** Retrieve relevant document chunks using ChromaDB.
- **Local LLM Integration:** Generate responses using Ollama and Llama 3.2 (3B).
- **Multi-Document Conversations:** Attach multiple PDFs to a conversation.
- **Conversation History:** Store conversations and messages using SQLite.
- **Knowledge Base Management:** View indexed documents, pages, and chunks.
- **Duplicate Detection:** Use SHA-256 hashing to identify previously uploaded files.
- **Local Processing:** Run the AI pipeline locally without requiring a cloud LLM API.

## Architecture

```text
                 React Frontend
                       |
                       v
                 FastAPI Backend
                       |
             +---------+---------+
             |                   |
             v                   v
        PDF Processing      Conversation
        and Chunking        Management
             |                   |
             v                   v
       Nomic Embeddings        SQLite
             |
             v
          ChromaDB
       Vector Database
             |
             v
       Relevant Chunks
             |
             v
        RAG Generator
             |
             v
       Ollama - Llama 3.2
             |
             v
        Generated Answer
             |
             v
         React UI
```

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Python, FastAPI |
| LLM Runtime | Ollama |
| Language Model | Llama 3.2 (3B) |
| Embedding Model | Nomic Embed Text |
| Vector Database | ChromaDB |
| Relational Database | SQLite |
| PDF Processing | Python PDF extraction libraries |
| API Communication | REST API |

## Project Structure

```text
Local-AI-Knowledge-Assistant/
│
├── backend/
│   ├── embeddings/
│   │   └── embedding_model.py
│   │
│   ├── ingestion/
│   │   ├── pdf_loader.py
│   │   ├── text_splitter.py
│   │   └── ...
│   │
│   ├── rag/
│   │   ├── generator.py
│   │   ├── retriever.py
│   │   └── test_rag.py
│   │
│   ├── services/
│   │   ├── conversation_service.py
│   │   ├── document_processor.py
│   │   └── document_registry.py
│   │
│   ├── vectorstore/
│   │   └── chroma_db.py
│   │
│   ├── main.py
│   ├── database.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── package-lock.json
│
├── .gitignore
└── README.md
```

## Prerequisites

Install the following before running the application:

- Python 3.12
- Node.js and npm
- Ollama
- Git

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git

cd YOUR_REPOSITORY
```

### 2. Set up the Python environment

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

### 3. Download local Ollama models

Install Ollama, then run:

```bash
ollama pull llama3.2:3b
```

Download the embedding model:

```bash
ollama pull nomic-embed-text
```

Ensure Ollama is running before starting the backend.

### 4. Start the backend

```powershell
cd backend

python -m uvicorn main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the frontend

Open another terminal:

```powershell
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:5173
```

## How RAG Works in This Application

1. The user uploads a PDF.
2. The backend extracts text from the PDF.
3. Extracted text is divided into smaller chunks.
4. Nomic generates embeddings for the chunks.
5. ChromaDB stores the embeddings with document metadata.
6. The user's question is converted into a query embedding.
7. ChromaDB retrieves relevant chunks through semantic similarity search.
8. The retrieved context is passed to Llama 3.2 through Ollama.
9. The generated answer and source information are displayed in the React interface.

## Privacy and Data Storage

The application is designed to run locally.

- LLM inference runs through Ollama.
- Vector embeddings are stored in ChromaDB.
- Conversation history is stored in SQLite.
- Uploaded documents are processed by the local backend.

The repository excludes local databases, uploaded PDFs, environment files, and virtual environments. Users create their own local data when running the application.

## Future Improvements

- Improve retrieval quality using hybrid search.
- Add reranking for better context selection.
- Implement streaming LLM responses.
- Add document-level retrieval evaluation.
- Improve hallucination detection and answer grounding.
- Support additional document formats.
- Add automated testing for RAG pipelines.
- Add Docker-based deployment.

## Author

**Bhagath Naidu**

B.Tech – Computer Science and Business Systems


---

