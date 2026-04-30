import os
import fitz  # PyMuPDF
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict


def load_and_chunk_pdf(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict]:
    """
    Load a PDF and split it into chunks with rich metadata.
    Uses cross-page chunking to maintain semantic context across page boundaries.
    Each chunk carries page number, position, and document metadata.

    Returns:
        List of dicts: [{"text": ..., "page": ..., "metadata": {...}}, ...]
    """
    import re
    doc = fitz.open(file_path)
    
    # Extract document-level metadata
    doc_metadata = {
        "total_pages": len(doc),
        "file_path": file_path
    }
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    full_text_list = []
    page_map = []  # List of tuples: (start_char, end_char, page_num)
    current_char_index = 0
    
    full_text_for_saving = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        if not text:
            continue

        # Light text normalization: replace 3+ newlines with 2
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Accumulate text for full text extraction saving
        full_text_for_saving.append(f"--- PAGE {page_num + 1} ---\n{text}\n")

        # Add a separator between pages to ensure paragraphs don't accidentally merge without spaces
        if current_char_index > 0:
            separator = "\n\n"
            full_text_list.append(separator)
            current_char_index += len(separator)

        start_char = current_char_index
        end_char = current_char_index + len(text)

        page_map.append((start_char, end_char, page_num + 1))

        full_text_list.append(text)
        current_char_index = end_char

    doc.close()

    # Join the full text
    full_text = "".join(full_text_list)
    
    # Split full text into chunks
    chunks = splitter.split_text(full_text)

    all_chunks = []
    
    # Track position in the full text for mapping chunks back to pages
    search_start = 0

    for chunk_idx, chunk in enumerate(chunks):
        # Find the chunk's start index in the full text
        chunk_start = full_text.find(chunk[:50], search_start)
        if chunk_start == -1:
            chunk_start = search_start  # Fallback
            
        chunk_end = chunk_start + len(chunk)
        search_start = max(0, chunk_start)  # Move search window forward
        
        # Determine which page(s) this chunk belongs to
        spanned_pages = []
        primary_page_num = None
        
        for p_start, p_end, p_num in page_map:
            # Check for overlap
            if max(chunk_start, p_start) < min(chunk_end, p_end):
                spanned_pages.append(p_num)
                if primary_page_num is None:
                    primary_page_num = p_num
        
        if not spanned_pages:
            # Fallback if no overlap found
            if page_map:
                primary_page_num = page_map[-1][2]
                spanned_pages = [primary_page_num]
            else:
                primary_page_num = 1
                spanned_pages = [1]
                
        chunk_metadata = {
            **doc_metadata,
            "chunk_index": chunk_idx,
            "spanned_pages": spanned_pages,
            "chunk_size": len(chunk),
            "word_count": len(chunk.split())
        }
        
        all_chunks.append({
            "text": chunk,
            "page": primary_page_num,  # Primary starting page
            "metadata": chunk_metadata
        })

    # Save full extracted text to file
    if full_text_for_saving:
        _save_extracted_text(file_path, full_text_for_saving)

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
