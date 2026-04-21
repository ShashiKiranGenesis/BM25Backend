# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Flask Frontend - Port 5000)                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Upload PDF  │  │ Toggle Mode  │  │ Ask Question │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                        (Port 8000)                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    API ROUTERS                           │ │
│  │  /upload  /ask  /status  /refresh  /documents           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   RAG SERVICE                            │ │
│  │         (Orchestrates the entire pipeline)               │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RETRIEVAL LAYER                            │
│                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐      │
│  │   BM25 Retriever    │         │  Vector Retriever   │      │
│  │   (Always Active)   │         │   (Optional)        │      │
│  │                     │         │                     │      │
│  │  • Keyword-based    │         │  • TF-IDF (default) │      │
│  │  • Fast & precise   │         │  • Transformers     │      │
│  │  • Top 15 chunks    │         │  • Top 15 chunks    │      │
│  └─────────────────────┘         └─────────────────────┘      │
│              │                              │                   │
│              └──────────────┬───────────────┘                   │
│                             ▼                                   │
│              ┌──────────────────────────────┐                  │
│              │   Merge & Deduplicate        │                  │
│              │   (Average scores)           │                  │
│              └──────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RERANKING LAYER                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  FlashRank Reranker                      │ │
│  │                                                          │ │
│  │  • Cross-encoder model                                  │ │
│  │  • Scores query-chunk relevance                         │ │
│  │  • Selects top 5 chunks                                 │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GENERATION LAYER                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Groq LLM API                          │ │
│  │                                                          │ │
│  │  • Model: llama-3.3-70b-versatile                       │ │
│  │  • Input: Question + Top 5 chunks                       │ │
│  │  • Output: Natural language answer                      │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RESPONSE                                │
│                                                                 │
│  {                                                              │
│    "answer": "...",                                             │
│    "source_chunks": [...]                                       │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Document Upload Flow

```
PDF File
   │
   ▼
┌──────────────────┐
│  PyMuPDF Loader  │  Extract text + metadata
└──────────────────┘
   │
   ▼
┌──────────────────┐
│  Text Splitter   │  RecursiveCharacterTextSplitter
│                  │  • chunk_size: 500
│                  │  • chunk_overlap: 50
└──────────────────┘
   │
   ▼
┌──────────────────┐
│  JSON Cache      │  Save to chunks/*.json
└──────────────────┘
   │
   ├─────────────────────┬─────────────────────┐
   ▼                     ▼                     ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐
│   BM25   │    │   TF-IDF     │    │  Metadata    │
│  Index   │    │   Vectors    │    │  JSON        │
└──────────┘    └──────────────┘    └──────────────┘
```

### 2. Query Flow (BM25 Only)

```
User Question
   │
   ▼
┌──────────────────┐
│  BM25 Retriever  │  Keyword matching
└──────────────────┘
   │
   ▼
┌──────────────────┐
│  Top 15 Chunks   │
└──────────────────┘
   │
   ▼
┌──────────────────┐
│  FlashRank       │  Rerank to top 5
└──────────────────┘
   │
   ▼
┌──────────────────┐
│  Groq LLM        │  Generate answer
└──────────────────┘
   │
   ▼
Answer + Sources
```

### 3. Query Flow (Hybrid Mode)

```
User Question
   │
   ├─────────────────────┬─────────────────────┐
   ▼                     ▼                     ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐
│   BM25   │    │   TF-IDF     │    │ Transformer  │
│ Top 15   │    │   Top 15     │    │  (optional)  │
└──────────┘    └──────────────┘    └──────────────┘
   │                     │                     │
   └─────────────────────┴─────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Merge & Dedup    │  Average scores
              │ Unique chunks    │
              └──────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  FlashRank       │  Rerank to top 5
              └──────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Groq LLM        │  Generate answer
              └──────────────────┘
                         │
                         ▼
              Answer + Sources
```

## Storage Architecture

```
backend/
│
├── uploads/                    # Original PDF files
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
│
├── chunks/                     # Cached JSON chunks
│   ├── document1_chunks.json
│   ├── document2_chunks.json
│   └── README.md
│
├── chroma_db/                  # Vector storage
│   ├── tfidf_vectorizer.pkl   # TF-IDF model
│   ├── chunks_data.pkl         # Chunk metadata
│   └── tfidf_vectors.pkl       # Precomputed vectors
│
└── MetaData.json               # Document metadata
    {
      "document1.pdf": {
        "hash": "abc123...",
        "chunks_count": 256,
        "processed_at": "2026-04-21...",
        ...
      }
    }
```

## Component Details

### BM25 Retriever

```python
Input:  Query string
Process:
  1. Tokenize query
  2. Compute BM25 scores for all chunks
  3. Sort by score descending
  4. Return top K chunks
Output: List[{text, score, metadata}]
```

### TF-IDF Vector Store

```python
Input:  Query string
Process:
  1. Transform query to TF-IDF vector
  2. Compute cosine similarity with all chunk vectors
  3. Sort by similarity descending
  4. Return top K chunks
Output: List[{text, score, metadata}]
```

### Merge & Deduplicate

```python
Input:  BM25 results + Vector results
Process:
  1. Create map: chunk_id -> chunk
  2. For duplicates: average scores
  3. Sort by combined score
Output: Merged list of unique chunks
```

### FlashRank Reranker

```python
Input:  Query + List of chunks
Process:
  1. Score each (query, chunk) pair
  2. Sort by relevance score
  3. Select top N
Output: Top N most relevant chunks
```

### Groq Generator

```python
Input:  Query + Top chunks
Process:
  1. Format prompt with context
  2. Call Groq API
  3. Stream response
Output: Natural language answer
```

## Configuration Matrix

| Component | Config Variable | Default | Options |
|-----------|----------------|---------|---------|
| Vector Backend | `VECTOR_BACKEND` | `tfidf` | `tfidf`, `transformer` |
| Embedding Model | `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Any sentence-transformers model |
| Chunk Size | `chunk_size` | 500 | 100-2000 |
| Chunk Overlap | `chunk_overlap` | 50 | 0-500 |
| BM25 Top K | `top_k` | 15 | 5-50 |
| Rerank Top N | `rerank_top_n` | 5 | 3-15 |
| LLM Model | Groq API | `llama-3.3-70b-versatile` | Any Groq model |

## Scalability

### Current Capacity
- **Documents**: Tested with 6 PDFs
- **Chunks**: 1082 chunks indexed
- **Memory**: ~60MB (TF-IDF)
- **Query Time**: ~400ms

### Scaling Considerations

**Horizontal Scaling**:
```
Load Balancer
    │
    ├─── FastAPI Instance 1
    ├─── FastAPI Instance 2
    └─── FastAPI Instance 3
         │
         └─── Shared Vector Store (Redis/PostgreSQL)
```

**Vertical Scaling**:
- More RAM → More chunks in memory
- More CPU → Faster retrieval
- GPU → Faster transformer embeddings

**Optimization**:
- Cache frequent queries
- Batch vector operations
- Use approximate nearest neighbors (FAISS)
- Implement query result caching

## Security

### Current Implementation
- ✅ Input validation (file types, sizes)
- ✅ Secure file handling (werkzeug)
- ✅ CORS configuration
- ✅ Environment variable secrets

### Production Recommendations
- Add authentication (JWT tokens)
- Rate limiting (per user/IP)
- Input sanitization (prevent injection)
- HTTPS/TLS encryption
- API key rotation
- Audit logging

## Monitoring

### Key Metrics
- Query latency (p50, p95, p99)
- Retrieval accuracy
- Cache hit rate
- Error rate
- Memory usage
- Disk usage

### Logging
```python
logger.info("Query received", extra={
    "question": question[:100],
    "use_vector": use_vector,
    "user_id": user_id
})

logger.info("Query completed", extra={
    "latency_ms": elapsed * 1000,
    "chunks_retrieved": len(chunks),
    "chunks_reranked": len(reranked)
})
```

## Future Enhancements

### Short Term
- [ ] Query caching
- [ ] Batch upload
- [ ] Export results
- [ ] Query history

### Medium Term
- [ ] Multi-language support
- [ ] Custom chunking strategies
- [ ] A/B testing framework
- [ ] Analytics dashboard

### Long Term
- [ ] Fine-tuned embeddings
- [ ] Graph-based retrieval
- [ ] Multi-modal support (images, tables)
- [ ] Federated search

---

**Architecture Version**: 3.0.0  
**Last Updated**: 2026-04-21  
**Status**: Production Ready
