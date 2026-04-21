import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_and_chunk_pdf(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict]:
    """
    Load a PDF and split it into chunks with rich metadata.
    Each chunk carries page number, position, and document metadata.

    Returns:
        List of dicts: [{"text": ..., "page": ..., "metadata": {...}}, ...]
    """
    logger.info(f"Loading and chunking PDF: {file_path}")
    
    doc = fitz.open(file_path)
    
    # Extract document-level metadata
    doc_metadata = {
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
        "producer": doc.metadata.get("producer", ""),
        "creation_date": doc.metadata.get("creationDate", ""),
        "modification_date": doc.metadata.get("modDate", ""),
        "total_pages": len(doc),
        "file_path": file_path
    }
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    all_chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        if not text:
            continue

        # Extract page-level metadata
        page_rect = page.rect
        page_metadata = {
            "page_width": page_rect.width,
            "page_height": page_rect.height,
            "page_rotation": page.rotation
        }

        # Split page text into smaller chunks
        chunks = splitter.split_text(text)

        for chunk_idx, chunk in enumerate(chunks):
            chunk_metadata = {
                **doc_metadata,  # Document-level metadata
                **page_metadata,  # Page-level metadata
                "chunk_index": chunk_idx,
                "chunks_on_page": len(chunks),
                "chunk_size": len(chunk),
                "word_count": len(chunk.split())
            }
            
            all_chunks.append({
                "text": chunk,
                "page": page_num + 1,  # 1-indexed page number
                "metadata": chunk_metadata
            })

    doc.close()

    logger.info(f"Loaded {len(all_chunks)} chunks from {len(doc)} pages")
    return all_chunks
