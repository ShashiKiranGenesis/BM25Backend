# Vector Retrieval Setup Guide

## Overview

The RAG system now supports **two retrieval modes**:

1. **BM25 Only** (default) - Fast keyword-based retrieval, no setup required
2. **Hybrid Mode** - Combines BM25 + semantic vector search for better results

## Quick Start

### Option 1: Pre-download the Model (Recommended)

Run this command **once** before starting the server:

```bash
python download_model.py
```

This downloads the embedding model (~90MB) to your local cache. The download may take 2-5 minutes depending on your internet connection.

### Option 2: Use a Smaller Model

If the download is too slow, edit `.env` and add:

```
EMBEDDING_MODEL=paraphrase-MiniLM-L3-v2
```

This model is smaller (61MB) and downloads faster, with slightly lower quality.

### Option 3: Let it Download on First Use

Simply start the server and use BM25 mode. When you first switch to Hybrid mode in the UI, the model will download automatically. The UI will show "falling back to BM25" until the download completes.

## How It Works

### Lazy Initialization

The vector store initializes **only when you first use Hybrid mode**. This means:

- ✅ Server starts immediately (no waiting for downloads)
- ✅ BM25 mode works right away
- ✅ Model downloads only when needed
- ✅ Download happens in the background

### First-Time Vector Query

When you first click "🧠 Hybrid" mode:

1. The embedding model starts downloading (you'll see progress in the terminal)
2. Your query falls back to BM25-only mode
3. Once downloaded, the model is cached permanently
4. All future Hybrid queries work instantly

### Persistent Storage

- Vector embeddings are stored in `chroma_db/` directory
- Embeddings persist across server restarts
- New documents are automatically embedded when uploaded
- No need to re-embed existing documents

## Troubleshooting

### Download Stuck at 0%

**Cause**: Slow or unstable internet connection

**Solutions**:
1. Wait longer - downloads can take 5-10 minutes on slow connections
2. Cancel (Ctrl+C) and retry - downloads resume from where they stopped
3. Use the smaller model (see Option 2 above)
4. Pre-download using `download_model.py` script

### "Vector retrieval failed" Error

**Cause**: Model download was interrupted

**Solution**: The system automatically falls back to BM25. Try Hybrid mode again after a few minutes.

### Behind a Corporate Proxy

Set these environment variables before running:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

## Model Information

### all-MiniLM-L6-v2 (Default)

- **Size**: 90.9 MB
- **Quality**: High
- **Speed**: Fast inference
- **Dimensions**: 384
- **Best for**: Production use

### paraphrase-MiniLM-L3-v2 (Alternative)

- **Size**: 61 MB
- **Quality**: Good
- **Speed**: Faster inference
- **Dimensions**: 384
- **Best for**: Quick testing, slow connections

## Checking Status

### Via API

```bash
curl http://localhost:8000/status
```

Look for `"vector_chunks"` in the response:
- `0` = Vector store not initialized yet
- `>0` = Vector store ready with embeddings

### Via Logs

Watch the terminal for:
- `"Initializing ChromaDB vector store"` - Download starting
- `"VectorStore ready"` - Download complete
- `"Vector retrieval failed"` - Download interrupted (falls back to BM25)

## Performance Notes

### Initial Embedding

When you first upload documents or refresh after enabling vector mode:
- Small docs (<100 pages): ~5-10 seconds
- Medium docs (100-500 pages): ~30-60 seconds  
- Large docs (>500 pages): ~2-5 minutes

Embeddings are cached, so this only happens once per document.

### Query Performance

- **BM25 Only**: ~100-200ms
- **Hybrid Mode**: ~300-500ms (includes embedding the query)

## Architecture

```
User Query
    ↓
[BM25 Retrieval] ← Always runs (fast, keyword-based)
    ↓
[Vector Retrieval] ← Optional (semantic similarity)
    ↓
[Merge & Deduplicate] ← Combines results, averages scores
    ↓
[FlashRank Reranker] ← Picks best 5 chunks
    ↓
[Groq LLM] ← Generates answer
```

## Frontend Integration

The UI provides a toggle:

- **⚡ BM25 Only** - Fast, keyword-based (default)
- **🧠 Hybrid** - BM25 + semantic vectors (better quality)

The mode is sent to the backend via the `use_vector` parameter.

## Need Help?

Check the logs in the terminal where you ran `python server.py`. All vector-related operations are logged with clear messages.
