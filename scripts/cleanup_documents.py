#!/usr/bin/env python3
"""
Clean Refresh Script for RAG System
====================================
This script wipes out all uploaded documents and resets the RAG system to a clean state.

What it deletes:
  - All PDF files in data/docs/
  - All chunk JSON files in data/chunks/
  - Resets metadata.json to empty state

The in-memory retriever will be reset when the app restarts.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# Find project root (where data/ and metadata.json are located)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent  # Go up one level from scripts/

# Configuration - use absolute paths
UPLOADS_DIR = str(PROJECT_ROOT / "data" / "docs")
CHUNKS_DIR = str(PROJECT_ROOT / "data" / "chunks")
EXTRACTED_TEXT_DIR = str(PROJECT_ROOT / "data" / "extracted_text")
METADATA_FILE = str(PROJECT_ROOT / "metadata.json")


def get_logger():
    """Simple logger for cleanup output."""
    def log(level, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level:8s} | {message}")
    
    return {
        "info": lambda msg: log("INFO", msg),
        "warning": lambda msg: log("WARNING", msg),
        "error": lambda msg: log("ERROR", msg),
        "success": lambda msg: log("SUCCESS", msg),
    }


logger = get_logger()


def count_files(directory):
    """Count files in a directory."""
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])


def delete_directory_contents(directory, pattern_filter=None):
    """Delete all files in a directory, optionally filtered by pattern."""
    if not os.path.exists(directory):
        logger["warning"](f"Directory does not exist: {directory}")
        return 0
    
    deleted_count = 0
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Apply filter if specified
            if pattern_filter and not filename.endswith(pattern_filter):
                continue
            
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1
                logger["info"](f"  Deleted: {filename}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_count += 1
                logger["info"](f"  Deleted directory: {filename}")
    
    except Exception as e:
        logger["error"](f"Error deleting files from {directory}: {e}")
        return -1
    
    return deleted_count


def reset_metadata():
    """Reset metadata.json to empty state."""
    try:
        empty_metadata = {
            "documents": {},
            "last_updated": datetime.now().isoformat(),
            "total_chunks": 0,
            "total_documents": 0
        }
        
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(empty_metadata, f, indent=2, ensure_ascii=False)
        
        logger["success"](f"Reset {METADATA_FILE} to empty state")
        return True
    
    except Exception as e:
        logger["error"](f"Error resetting metadata: {e}")
        return False


def cleanup_rag_system():
    """Main cleanup function."""
    print("\n" + "="*70)
    print("RAG SYSTEM CLEAN REFRESH")
    print("="*70)
    print(f"\n⚠️  WARNING: This will delete ALL uploaded documents and data!")
    print(f"    - PDF files from: {UPLOADS_DIR}")
    print(f"    - Chunk files from: {CHUNKS_DIR}")
    print(f"    - Extracted text files from: {EXTRACTED_TEXT_DIR}")
    print(f"    - Reset metadata file: {METADATA_FILE}")
    
    response = input("\n❓ Are you sure you want to continue? (yes/no): ").strip().lower()
    
    if response != "yes":
        logger["info"]("Cleanup cancelled by user")
        print("\n✗ Cleanup cancelled.\n")
        return False
    
    print("\n" + "-"*70)
    print("Starting cleanup...\n")
    
    stats = {
        "pdfs_deleted": 0,
        "chunks_deleted": 0,
        "extracted_text_deleted": 0,
        "metadata_reset": False,
        "errors": 0
    }
    
    # Count before
    logger["info"](f"Current state:")
    logger["info"](f"  PDF files in {UPLOADS_DIR}: {count_files(UPLOADS_DIR)}")
    logger["info"](f"  Chunk files in {CHUNKS_DIR}: {count_files(CHUNKS_DIR)}")
    logger["info"](f"  Extracted text files in {EXTRACTED_TEXT_DIR}: {count_files(EXTRACTED_TEXT_DIR)}")
    
    print()
    
    # Delete PDF files
    logger["info"](f"Deleting PDF files from {UPLOADS_DIR}...")
    deleted = delete_directory_contents(UPLOADS_DIR, ".pdf")
    if deleted >= 0:
        stats["pdfs_deleted"] = deleted
        logger["success"](f"Deleted {deleted} PDF file(s)")
    else:
        stats["errors"] += 1
    
    print()
    
    # Delete chunk JSON files
    logger["info"](f"Deleting chunk files from {CHUNKS_DIR}...")
    deleted = delete_directory_contents(CHUNKS_DIR, ".json")
    if deleted >= 0:
        stats["chunks_deleted"] = deleted
        logger["success"](f"Deleted {deleted} chunk file(s)")
    else:
        stats["errors"] += 1
    
    print()
    
    # Delete extracted text files
    logger["info"](f"Deleting extracted text files from {EXTRACTED_TEXT_DIR}...")
    deleted = delete_directory_contents(EXTRACTED_TEXT_DIR, ".txt")
    if deleted >= 0:
        stats["extracted_text_deleted"] = deleted
        logger["success"](f"Deleted {deleted} extracted text file(s)")
    else:
        stats["errors"] += 1
    
    print()
    
    # Reset metadata
    logger["info"](f"Resetting {METADATA_FILE}...")
    if reset_metadata():
        stats["metadata_reset"] = True
    else:
        stats["errors"] += 1
    
    # Summary
    print("\n" + "-"*70)
    print("CLEANUP SUMMARY")
    print("-"*70)
    print(f"✓ PDF files deleted:           {stats['pdfs_deleted']}")
    print(f"✓ Chunk files deleted:         {stats['chunks_deleted']}")
    print(f"✓ Extracted text files deleted: {stats['extracted_text_deleted']}")
    print(f"✓ Metadata reset:              {'Yes' if stats['metadata_reset'] else 'No'}")
    if stats["errors"] > 0:
        print(f"✗ Errors encountered:    {stats['errors']}")
    
    print("\n" + "-"*70)
    
    if stats["errors"] == 0:
        logger["success"]("Cleanup completed successfully!")
        print("💡 Tip: Restart the RAG server to reinitialize with empty documents.\n")
        return True
    else:
        logger["error"]("Cleanup completed with errors!")
        print("⚠️  Some operations failed. Check the logs above.\n")
        return False


if __name__ == "__main__":
    success = cleanup_rag_system()
    exit(0 if success else 1)
