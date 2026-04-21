# ChromaDB Vector Integration Summary

## What Was Done

### Backend Changes

1. **`backend/requirements.txt`**
   - Added `chromadb==1.5.8` (persistent vector store with pre-built wheels)
   - Added `sentence-transformers==3.4.1` (for embeddings)

2. **`backend/config.py`**
   - Added `CHROMA_DIR` (default: `chroma_db/`) — persistent storage location
   - Added `EMBEDDING_MODEL` (default: `all-MiniLM-L6-v2`) — fast, no GPU needed
   - Added `CHROMA_COLLECTION` (default: `rag_documents`)
   - Updated app title/description to reflect hybrid capabilities

3. **`backend/app/rag/vector_store.py`** (NEW)
   - `VectorStore` class wrapping ChromaDB with persistent storage
   - Stable chunk IDs: `{filename}_p{page}_c{chunk_index}` for idempotent re-uploads
   - Flattens nested metadata to ChromaDB-compatible format, reconstructs on query
   - Cosine distance → similarity score (0–1) to match BM25 score shape
   - Methods: `upsert_chunks()`, `query()`, `delete_document()`, `count()`

4. **`backend/app/rag/document_manager.py`**
   - Added `set_vector_store()` injection method (avoids circular imports)
   - After `process_document()` saves chunks to JSON, also calls `vector_store.upsert_chunks()`
   - New/changed documents are automatically embedded

5. **`backend/app/services/rag_service.py`**
   - `initialize_rag()` creates persistent `VectorStore` singleton on first call
   - `run_rag_pipeline()` accepts `use_vector: bool = False`
   - When `use_vector=True`:
     - Runs both BM25 and vector retrieval (top_k each)
     - Merges results, deduplicating by chunk identity
     - Averages scores for chunks appearing in both result sets
     - Reranks the combined pool with FlashRank
   - BM25-only mode unchanged (default)

6. **`backend/app/models/schemas.py`**
   - `QueryRequest` gets `use_vector: Optional[bool] = False`

7. **`backend/app/routers/query.py`**
   - Passes `use_vector` through to `run_rag_pipeline()`

8. **`backend/app/routers/documents.py`**
   - `/status` endpoint now also returns `vector_chunks` count

### Frontend Changes

1. **`frontend/templates/index.html`**
   - Updated title and header to reflect hybrid capabilities
   - Added **Retrieval Mode Toggle** section with two buttons:
     - **⚡ BM25 Only** — keyword retrieval (default)
     - **🧠 Hybrid** — BM25 + ChromaDB semantic search
   - Info box dynamically updates to explain the selected mode

2. **`frontend/static/js/main.js`**
   - Added `retrievalMode` state variable (`'bm25'` | `'hybrid'`)
   - Added `setRetrievalMode(mode)` function to toggle between modes
   - Updated `askQuestion()` to:
     - Set `use_vector = (retrievalMode === 'hybrid')`
     - Pass `use_vector` in the API request
     - Display a mode badge in the answer header showing which mode was used

3. **`frontend/static/css/style.css`**
   - Added styles for `.retrieval-toggle`, `.mode-btn`, `.mode-info`
   - Added `.badge-bm25` and `.badge-hybrid` for answer header badges

---

## How It Works

### Document Upload Flow
1. User uploads PDF → saved to `uploads/`
2. `initialize_rag()` called → `load_all_documents()`
3. For each new/changed document:
   - `process_document()` chunks the PDF
   - Saves chunks to `chunks/{filename}_chunks.json`
   - Calls `vector_store.upsert_chunks()` → embeddings generated and stored in `chroma_db/`
4. BM25 index built in memory from all chunks

### Query Flow (BM25 Only)
1. User asks question with `use_vector=false` (default)
2. BM25 retrieves top 15 chunks
3. FlashRank reranks to top 5
4. LLM generates answer

### Query Flow (Hybrid)
1. User asks question with `use_vector=true`
2. **BM25** retrieves top 15 chunks (keyword-based)
3. **ChromaDB** retrieves top 15 chunks (semantic similarity)
4. **Merge & deduplicate**:
   - Chunks appearing in both get averaged scores
   - Unique chunks keep their original scores
5. FlashRank reranks the combined pool to top 5
6. LLM generates answer

---

## Persistence

- **ChromaDB**: `chroma_db/` directory (persistent, survives restarts)
- **Chunks cache**: `chunks/*.json` (fast reload, hash-based change detection)
- **Metadata**: `MetaData.json` (document info, chunk counts)

On first startup with existing documents, the vector store will be empty. Run `POST /refresh` to populate it.

---

## Configuration

Environment variables (`.env`):
```bash
CHROMA_DIR=chroma_db                # Where ChromaDB stores data
EMBEDDING_MODEL=all-MiniLM-L6-v2    # Sentence-transformers model
CHROMA_COLLECTION=rag_documents     # Collection name
```

---

## API Changes

### `POST /ask`
**Request:**
```json
{
  "question": "What is augmented reality?",
  "top_k": 15,
  "rerank_top_n": 5,
  "filter_files": ["doc1.pdf", "doc2.pdf"],
  "use_vector": false  // NEW: true for hybrid, false for BM25-only
}
```

**Response:** (unchanged)

### `GET /status`
**Response:**
```json
{
  "ready": true,
  "total_documents": 6,
  "total_chunks": 526,
  "vector_chunks": 526,  // NEW: count of embeddings in ChromaDB
  "last_updated": "2026-04-20T15:38:51",
  "documents": { ... }
}
```

---

## User Experience

1. **Default behavior unchanged**: BM25-only retrieval works exactly as before
2. **Opt-in hybrid mode**: User clicks "🧠 Hybrid" button to enable vector search
3. **Visual feedback**: Answer header shows which mode was used
4. **Info box**: Explains the selected mode in plain language

---

## Performance Notes

- **BM25 only**: Fast, no GPU needed, works immediately
- **Hybrid mode**: Slower (embeddings + merge), but better semantic recall
- **First-time embedding**: Happens on document upload/refresh (one-time cost per document)
- **Embedding model**: `all-MiniLM-L6-v2` is lightweight (80MB), runs on CPU

---

## Testing

1. Start backend: `cd backend && venv/Scripts/python server.py`
2. Start frontend: `cd frontend && venv/Scripts/python app.py`
3. Upload a PDF or run `POST /refresh`
4. Ask a question with BM25 mode (default)
5. Switch to Hybrid mode and ask the same question
6. Compare results — hybrid should surface semantically similar chunks that BM25 might miss
