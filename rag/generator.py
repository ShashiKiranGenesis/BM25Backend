from openai import AsyncOpenAI
from typing import List, Dict
import os
import logging

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY is not set")
        raise RuntimeError(
            "GROQ_API_KEY is not set. Make sure your .env file is present and load_dotenv() is called before importing this module."
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )


def build_prompt(question: str, chunks: List[Dict]) -> str:
    """Build the RAG prompt with retrieved context and metadata."""
    context_parts = []
    
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        doc_metadata = chunk.get('document_metadata', {})
        
        # Build context with enhanced metadata
        context_header = f"[DOC] {chunk.get('source_file', 'Unknown')} | Page {chunk['page']}"
        
        if metadata.get('word_count'):
            context_header += f" | {metadata['word_count']} words"
        if metadata.get('chunk_index') is not None:
            context_header += f" | Chunk {metadata['chunk_index'] + 1}"
        if doc_metadata.get('author'):
            context_header += f" | Author: {doc_metadata['author']}"
        if doc_metadata.get('category'):
            context_header += f" | Category: {doc_metadata['category']}"
        
        context_header += "]"
        
        context_parts.append(f"{context_header}: {chunk['text']}")
    
    context = "\n\n".join(context_parts)
    
    # Add document collection info if available
    doc_info = ""
    if chunks:
        unique_docs = set()
        for chunk in chunks:
            doc_meta = chunk.get('document_metadata', {})
            if chunk.get('source_file'):
                unique_docs.add(f"{chunk['source_file']} ({doc_meta.get('author', 'Unknown Author')})")
        
        if unique_docs:
            doc_info = f"Sources: {', '.join(sorted(unique_docs))}\n\n"

    prompt = f"""You are a helpful assistant. Answer the user's question using the context provided below.
Use the context as your primary source. If the answer is partially present, synthesize it from the available information.
Only say "I could not find the answer in the provided document." if the topic is completely absent from the context.

{doc_info}Context:
{context}

Question: {question}

Answer:"""

    return prompt

async def generate_answer(question: str, chunks: List[Dict]) -> str:
    """
    Call OpenAI to generate an answer from the reranked chunks.

    Args:
        question: User question
        chunks:   Reranked top chunks

    Returns:
        LLM generated answer string
    """
    logger.debug(f"Generating answer for question: '{question}' using {len(chunks)} chunks")
    
    prompt = build_prompt(question, chunks)

    client = _get_client()
    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=512
    )
    answer = response.choices[0].message.content.strip()
    logger.debug(f"Generated answer: {answer[:100]}...")
    return answer
