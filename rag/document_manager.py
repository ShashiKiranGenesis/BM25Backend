import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from .loader import load_and_chunk_pdf

METADATA_FILE = "MetaData.json"
UPLOADS_DIR = "uploads"


class DocumentManager:
    def __init__(self):
        self.metadata_file = METADATA_FILE
        self.uploads_dir = UPLOADS_DIR
        self.metadata = self._load_metadata()
        
    def _ensure_enhanced_metadata(self, filename: str, doc_info: Dict) -> Dict:
        """Ensure document has all enhanced metadata fields."""
        defaults = {
            "author": "Admin",
            "category": "General", 
            "department": "Unknown",
            "doc_type": "PDF Document",
            "version": "1.0",
            "description": f"Auto-processed document: {filename}",
            "date_uploaded": doc_info.get("processed_at", datetime.now().isoformat()),
            "tags": []
        }
        
        # Add missing fields
        for key, default_value in defaults.items():
            if key not in doc_info:
                doc_info[key] = default_value
        
        return doc_info
    
    def _load_metadata(self) -> Dict:
        """Load metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Default metadata structure
        return {
            "documents": {},
            "last_updated": None,
            "total_chunks": 0,
            "total_documents": 0
        }
    
    def _save_metadata(self):
        """Save metadata to JSON file."""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_file_info(self, file_path: str) -> Dict:
        """Get file information."""
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hash": self._get_file_hash(file_path)
        }
    
    def scan_uploads_directory(self) -> List[str]:
        """Scan uploads directory for PDF files."""
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir, exist_ok=True)
            return []
        
        pdf_files = []
        for file in os.listdir(self.uploads_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(self.uploads_dir, file))
        
        return pdf_files
    
    def needs_processing(self, file_path: str) -> bool:
        """Check if file needs processing (new or changed)."""
        filename = os.path.basename(file_path)
        
        # File not in metadata
        if filename not in self.metadata["documents"]:
            return True
        
        # Check if file changed
        current_info = self._get_file_info(file_path)
        stored_info = self.metadata["documents"][filename]
        
        return (
            current_info["hash"] != stored_info.get("hash") or
            current_info["size"] != stored_info.get("size") or
            current_info["modified"] != stored_info.get("modified")
        )
    
    def update_document_metadata(self, filename: str, metadata_updates: Dict):
        """Update metadata for an existing document."""
        if filename in self.metadata["documents"]:
            self.metadata["documents"][filename].update(metadata_updates)
            self._save_metadata()
            return True
        return False
    
    def process_document(self, file_path: str, additional_metadata: Dict = None) -> List[Dict]:
        """Process a single PDF document with enhanced metadata."""
        print(f"Processing: {file_path}")
        
        # Load and chunk the PDF
        chunks = load_and_chunk_pdf(file_path)
        
        # Store metadata
        filename = os.path.basename(file_path)
        file_info = self._get_file_info(file_path)
        
        # Enhanced metadata with defaults
        enhanced_metadata = {
            **file_info,
            "chunks_count": len(chunks),
            "processed_at": datetime.now().isoformat(),
            "file_path": file_path,
            "date_uploaded": datetime.now().isoformat(),
            "author": "Admin",  # Default author
            "category": "General",
            "department": "Unknown",
            "doc_type": "PDF Document",
            "version": "1.0",
            "description": f"Auto-processed document: {filename}",
            "tags": []
        }
        
        # Override with any provided metadata
        if additional_metadata:
            enhanced_metadata.update(additional_metadata)
        
        # Add document info to chunks
        for chunk in chunks:
            chunk["source_file"] = filename
            chunk["file_path"] = file_path
            chunk["document_metadata"] = {
                "author": enhanced_metadata["author"],
                "category": enhanced_metadata["category"],
                "department": enhanced_metadata["department"],
                "doc_type": enhanced_metadata["doc_type"],
                "version": enhanced_metadata["version"],
                "description": enhanced_metadata["description"],
                "date_uploaded": enhanced_metadata["date_uploaded"]
            }
        
        # Update metadata
        self.metadata["documents"][filename] = enhanced_metadata
        
        return chunks
    
    def load_all_documents(self) -> List[Dict]:
        """Load and process all documents, returning combined chunks."""
        pdf_files = self.scan_uploads_directory()
        all_chunks = []
        
        if not pdf_files:
            print("No PDF files found in uploads directory")
            return []
        
        print(f"Found {len(pdf_files)} PDF files")
        
        # Process each file
        for file_path in pdf_files:
            if self.needs_processing(file_path):
                try:
                    chunks = self.process_document(file_path)
                    all_chunks.extend(chunks)
                    print(f"✓ Processed {os.path.basename(file_path)}: {len(chunks)} chunks")
                except Exception as e:
                    print(f"✗ Error processing {file_path}: {e}")
            else:
                print(f"⚡ Skipping {os.path.basename(file_path)} (unchanged)")
                # Load chunks for unchanged files while preserving metadata
                try:
                    chunks = load_and_chunk_pdf(file_path)
                    filename = os.path.basename(file_path)
                    stored_metadata = self.metadata["documents"][filename]
                    
                    for chunk in chunks:
                        chunk["source_file"] = filename
                        chunk["file_path"] = file_path
                        chunk["document_metadata"] = {
                            "author": stored_metadata.get("author", "Admin"),
                            "category": stored_metadata.get("category", "General"),
                            "department": stored_metadata.get("department", "Unknown"),
                            "doc_type": stored_metadata.get("doc_type", "PDF Document"),
                            "version": stored_metadata.get("version", "1.0"),
                            "description": stored_metadata.get("description", f"Document: {filename}"),
                            "date_uploaded": stored_metadata.get("date_uploaded", stored_metadata.get("processed_at"))
                        }
                    all_chunks.extend(chunks)
                    
                    # Ensure metadata is preserved and not overwritten
                    # Only update file info, keep enhanced metadata
                    current_file_info = self._get_file_info(file_path)
                    
                    # Preserve existing enhanced metadata
                    enhanced_metadata = self._ensure_enhanced_metadata(filename, stored_metadata)
                    
                    # Update with current file info
                    enhanced_metadata.update({
                        "size": current_file_info["size"],
                        "modified": current_file_info["modified"],
                        "hash": current_file_info["hash"],
                        "chunks_count": len(chunks),
                        "file_path": file_path
                    })
                    
                    self.metadata["documents"][filename] = enhanced_metadata
                    
                except Exception as e:
                    print(f"✗ Error loading {file_path}: {e}")
        
        # Update totals
        self.metadata["total_chunks"] = len(all_chunks)
        self.metadata["total_documents"] = len([f for f in pdf_files if os.path.exists(f)])
        
        # Save metadata
        self._save_metadata()
        
        print(f"📚 Loaded {len(all_chunks)} total chunks from {self.metadata['total_documents']} documents")
        
        return all_chunks
    
    def get_document_info(self) -> Dict:
        """Get summary information about loaded documents."""
        return {
            "total_documents": self.metadata["total_documents"],
            "total_chunks": self.metadata["total_chunks"],
            "last_updated": self.metadata["last_updated"],
            "documents": {
                filename: {
                    "chunks_count": info["chunks_count"],
                    "size": info["size"],
                    "processed_at": info["processed_at"],
                    "author": info.get("author", "Admin"),
                    "category": info.get("category", "General"),
                    "department": info.get("department", "Unknown"),
                    "doc_type": info.get("doc_type", "PDF Document"),
                    "version": info.get("version", "1.0"),
                    "description": info.get("description", f"Document: {filename}"),
                    "date_uploaded": info.get("date_uploaded", info.get("processed_at"))
                }
                for filename, info in self.metadata["documents"].items()
            }
        }