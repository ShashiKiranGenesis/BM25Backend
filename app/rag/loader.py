import os
import fitz  # PyMuPDF
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict


def load_and_chunk_pdf(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict]:
    """
    Load a PDF and split it into chunks with rich metadata.
    Each chunk carries page number, position, and document metadata.

    Returns:
        List of dicts: [{"text": ..., "page": ..., "metadata": {...}}, ...]
    """
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
    full_text = []  # Accumulate all text for extraction

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        if not text:
            continue

        # Accumulate text for full text extraction
        full_text.append(f"--- PAGE {page_num + 1} ---\n{text}\n")

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

    # Save full extracted text to file
    if full_text:
        _save_extracted_text(file_path, full_text)

    return all_chunks


def _save_extracted_text(file_path: str, full_text: List[str]) -> None:
    """
    Save the full extracted text to a .txt file in data/extracted_text folder.
    
    Args:
        file_path: Path to the original PDF file
        full_text: List of text chunks from all pages
    """
    try:
        # Get the filename without extension
        filename = Path(file_path).stem
        
        # Create extracted_text directory if it doesn't exist
        extracted_text_dir = Path("data") / "extracted_text"
        extracted_text_dir.mkdir(parents=True, exist_ok=True)
        
        # Create output file path
        output_file = extracted_text_dir / f"{filename}.txt"
        
        # Write full text to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(full_text))
        
        print(f"✓ Extracted text saved to: {output_file}")
    
    except Exception as e:
        print(f"⚠️  Warning: Failed to save extracted text: {e}")
