# Backend - Vectorless RAG API

A FastAPI-based Retrieval-Augmented Generation (RAG) system that uses BM25 retrieval, FlashRank reranking, and LLM generation without requiring a vector database.

## Overview

This backend provides a lightweight RAG solution that:
- Uses **BM25** for initial document retrieval (no vector embeddings needed)
- Applies **FlashRank** for reranking results
- Generates answers using **Groq LLM**
- Manages PDF documents with metadata tracking
- Provides RESTful API endpoints for document management and question answering

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌─────────┐
│   PDF Docs  │ --> │ BM25 Retrieval│ --> │  Reranker  │ --> │   LLM   │
└─────────────┘     └──────────────┘     └────────────┘     └─────────┘
```

## Features

- 📄 **PDF Document Processing**: Upload and process PDF files automatically
- 🔍 **BM25 Retrieval**: Fast keyword-based search without vector databases
- 🎯 **Smart Reranking**: FlashRank reranker for improved relevance
- 🤖 **LLM Generation**: Groq-powered answer generation
- 📊 **Metadata Management**: Track document metadata (author, category, tags, etc.)
- 🔄 **Auto-refresh**: Reload documents from uploads directory
- 🎛️ **Configurable**: Adjust top_k, rerank_top_n, and filter by files

## Project Structure

```
backend/
├── main.py                 # FastAPI application and routes
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── MetaData.json          # Document metadata storage
├── uploads/               # PDF documents directory
└── rag/
    ├── document_manager.py  # Document loading and metadata
    ├── loader.py           # PDF text extraction
    ├── retriever.py        # BM25 retrieval implementation
    ├── reranker.py         # FlashRank reranking
    └── generator.py        # LLM answer generation
```

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   
   Create a `.env` file in the backend directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

   Get your Groq API key from: https://console.groq.com/

4. **Add PDF documents**:
   
   Place your PDF files in the `uploads/` directory.

## Usage

### Start the Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. Root
```http
GET /
```
Returns API information and available endpoints.

### 2. System Status
```http
GET /status
```
Check system status and document information.

**Response**:
```json
{
  "ready": true,
  "total_documents": 4,
  "total_chunks": 502,
  "last_updated": "2026-04-20T15:39:27.358664",
  "documents": {
    "example.pdf": {
      "chunks_count": 100,
      "author": "Admin",
      "category": "General"
    }
  }
}
```

### 3. Upload PDF
```http
POST /upload
Content-Type: multipart/form-data
```

Upload a new PDF document.

**Request**:
- `file`: PDF file (multipart/form-data)

**Response**:
```json
{
  "success": true,
  "message": "PDF uploaded successfully!",
  "filename": "document.pdf",
  "total_documents": 5,
  "total_chunks": 602
}
```

### 4. Refresh Documents
```http
POST /refresh
```

Reload all documents from the uploads directory.

### 5. Ask Question
```http
POST /ask
Content-Type: application/json
```

Ask a question and get an AI-generated answer with sources.

**Request**:
```json
{
  "question": "What is augmented reality?",
  "top_k": 15,
  "rerank_top_n": 5,
  "filter_files": ["document1.pdf", "document2.pdf"]
}
```

**Parameters**:
- `question` (required): Your question
- `top_k` (optional, default: 15): Number of chunks to retrieve with BM25
- `rerank_top_n` (optional, default: 5): Number of chunks after reranking
- `filter_files` (optional): List of filenames to search within

**Response**:
```json
{
  "question": "What is augmented reality?",
  "answer": "Augmented reality (AR) is...",
  "source_chunks": [
    {
      "text": "Chunk text...",
      "page": 5,
      "score": 0.95,
      "source_file": "document.pdf",
      "file_path": "uploads/document.pdf",
      "metadata": {},
      "document_metadata": {
        "author": "Admin",
        "category": "General"
      }
    }
  ]
}
```

### 6. Update Metadata
```http
PUT /metadata/{filename}
Content-Type: application/json
```

Update metadata for a specific document.

**Request**:
```json
{
  "author": "John Doe",
  "category": "Research",
  "department": "Engineering",
  "tags": ["AI", "ML", "RAG"]
}
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for LLM | Yes |

### Document Metadata

Each document can have the following metadata:
- `author`: Document author
- `category`: Document category
- `department`: Department/team
- `doc_type`: Document type
- `version`: Version number
- `description`: Document description
- `tags`: List of tags

## RAG Components

### 1. Document Manager (`document_manager.py`)
- Loads PDF documents from uploads directory
- Manages document metadata
- Tracks document changes and updates

### 2. Loader (`loader.py`)
- Extracts text from PDF files using PyMuPDF
- Chunks documents using LangChain text splitters
- Preserves page numbers and metadata

### 3. Retriever (`retriever.py`)
- Implements BM25 algorithm for keyword-based retrieval
- Supports file filtering
- Returns top-k most relevant chunks

### 4. Reranker (`reranker.py`)
- Uses FlashRank for semantic reranking
- Improves relevance of retrieved chunks
- Configurable top-n results

### 5. Generator (`generator.py`)
- Generates answers using Groq LLM
- Combines context from reranked chunks
- Provides source attribution

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **PyMuPDF**: PDF text extraction
- **rank-bm25**: BM25 retrieval algorithm
- **flashrank**: Reranking model
- **langchain-text-splitters**: Text chunking
- **groq**: LLM API client
- **python-dotenv**: Environment variable management

## Troubleshooting

### No documents loaded
- Ensure PDF files are in the `uploads/` directory
- Check file permissions
- Call `/refresh` endpoint to reload documents

### API connection errors
- Verify the server is running on port 8000
- Check CORS settings if calling from frontend
- Ensure firewall allows connections

### LLM generation errors
- Verify `GROQ_API_KEY` is set correctly in `.env`
- Check Groq API quota and rate limits
- Review error messages in server logs

## Performance Tips

- Adjust `top_k` (15-30) for initial retrieval breadth
- Set `rerank_top_n` (3-7) for final context quality
- Use `filter_files` to search specific documents
- Larger chunks = more context but slower processing

## License

This project is part of a RAG system implementation.

## Support

For issues or questions, please check the API documentation at `/docs` or review the server logs.
