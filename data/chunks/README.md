# Chunks Directory

This directory stores the processed PDF chunks in JSON format for faster loading and caching.

## Purpose

When PDFs are processed, they are:
1. Extracted and split into text chunks
2. Enriched with metadata (page numbers, document info, etc.)
3. Saved as JSON files in this directory

## Benefits

- **Faster Loading**: Subsequent loads read from JSON instead of re-processing PDFs
- **Caching**: Unchanged documents load from cached JSON files
- **Portability**: Chunks can be backed up, shared, or analyzed independently
- **Debugging**: Easy to inspect what chunks were extracted from each document

## File Naming Convention

Each PDF generates a corresponding JSON file:
- `document.pdf` → `document_chunks.json`
- `My Report.pdf` → `My_Report_chunks.json`

Special characters in filenames are replaced with underscores for safety.

## JSON Structure

Each JSON file contains:

```json
{
  "document": "original_filename.pdf",
  "total_chunks": 256,
  "generated_at": "2026-04-20T15:38:51.296516",
  "chunks": [
    {
      "text": "The actual text content of the chunk...",
      "page": 1,
      "metadata": {
        "title": "Document Title",
        "author": "Document Author",
        "total_pages": 50,
        "chunk_index": 0,
        "chunks_on_page": 3,
        "chunk_size": 487,
        "word_count": 82,
        "page_width": 612.0,
        "page_height": 792.0
      },
      "source_file": "document.pdf",
      "file_path": "data/docs/document.pdf",
      "document_metadata": {
        "author": "Admin",
        "category": "General",
        "department": "Engineering",
        "doc_type": "PDF Document",
        "version": "1.0",
        "description": "Technical documentation",
        "date_uploaded": "2026-04-20T15:38:51.296528"
      }
    }
  ]
}
```

## Automatic Management

The system automatically:
- Creates this directory on first run
- Saves chunks when processing new PDFs
- Loads from JSON when documents haven't changed
- Re-generates JSON if the source PDF is modified

## Manual Operations

### View Chunks for a Document

```bash
# Pretty print JSON
cat data/chunks/document_chunks.json | python -m json.tool

# Count chunks
cat data/chunks/document_chunks.json | grep -o '"text"' | wc -l
```

### Clear Cache

To force re-processing of all documents:

```bash
# Delete all chunk files
rm data/chunks/*.json

# Or delete specific document chunks
rm data/chunks/specific_document_chunks.json
```

### Backup Chunks

```bash
# Backup all chunks
tar -czf chunks_backup_$(date +%Y%m%d).tar.gz data/chunks/

# Restore from backup
tar -xzf chunks_backup_20260420.tar.gz
```

## Performance Impact

- **First Load**: PDF → Text Extraction → Chunking → JSON Save (~2-5 seconds per PDF)
- **Cached Load**: JSON Read → Parse (~0.1-0.5 seconds per PDF)

Caching provides **10-50x faster** loading for unchanged documents.

## Storage Considerations

- JSON files are typically **1.5-3x** the size of extracted text
- Includes metadata overhead for each chunk
- Average: 500KB - 5MB per document depending on size

## Troubleshooting

### Chunks not being saved

Check:
1. Directory permissions (should be writable)
2. Disk space availability
3. Backend logs for error messages

### Stale chunks

If a PDF is updated but old chunks are still used:
1. Delete the corresponding JSON file
2. Restart the backend or call `/refresh` endpoint

### Corrupted JSON

If a JSON file is corrupted:
1. Delete the file: `rm data/chunks/problematic_document_chunks.json`
2. The system will regenerate it on next load

## Integration

The chunks are used by:
- **BM25 Retriever**: Searches across all chunks
- **Reranker**: Re-ranks retrieved chunks
- **Generator**: Uses top chunks as context for LLM

## Best Practices

1. **Keep in sync**: Don't manually edit JSON files
2. **Backup regularly**: Include chunks in your backup strategy
3. **Monitor size**: Large chunk directories may need cleanup
4. **Version control**: Consider excluding from git for large datasets

## Related Files

- `app/rag/document_manager.py` - Manages chunk saving/loading
- `app/rag/loader.py` - Extracts and chunks PDFs
- `metadata.json` - Tracks document metadata
- `data/docs/` - Source PDF files
