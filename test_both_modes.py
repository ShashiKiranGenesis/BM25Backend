"""
Quick test script to compare BM25-only vs Hybrid (BM25 + TF-IDF) modes.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_query(question: str, use_vector: bool, mode_name: str):
    """Test a single query and print results."""
    print(f"\n{'='*70}")
    print(f"Mode: {mode_name}")
    print(f"Question: {question}")
    print(f"{'='*70}")
    
    start = time.time()
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": question, "use_vector": use_vector},
        headers={"Content-Type": "application/json"}
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success ({elapsed:.2f}s)")
        print(f"\nAnswer:\n{data['answer']}\n")
        print(f"Sources ({len(data['source_chunks'])} chunks):")
        for i, chunk in enumerate(data['source_chunks'][:3], 1):
            print(f"  {i}. {chunk['source_file']} (page {chunk['page']}, score: {chunk['score']:.4f})")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def main():
    print("\n" + "="*70)
    print("RAG System Comparison Test")
    print("="*70)
    
    # Check server status
    try:
        status = requests.get(f"{BASE_URL}/status").json()
        print(f"\n📊 System Status:")
        print(f"   Documents: {status['total_documents']}")
        print(f"   BM25 Chunks: {status['total_chunks']}")
        print(f"   Vector Chunks: {status['vector_chunks']}")
    except Exception as e:
        print(f"\n❌ Cannot connect to server: {e}")
        return
    
    # Test questions
    questions = [
        "What is augmented reality?",
        "Explain cloud computing security",
    ]
    
    for question in questions:
        # Test BM25 only
        test_query(question, use_vector=False, mode_name="⚡ BM25 Only")
        
        # Test Hybrid
        test_query(question, use_vector=True, mode_name="🧠 Hybrid (BM25 + TF-IDF)")
    
    print(f"\n{'='*70}")
    print("Test Complete!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
