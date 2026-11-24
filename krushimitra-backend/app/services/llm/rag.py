"""Retrieval over the agronomy knowledge base (pgvector).

TODO (RAG pass):
  - embed the query (multilingual-e5 / BGE, dim 1024),
  - cosine search kb_chunks via pgvector,
  - return top-k snippets + citations.
Stub returns nothing so the copilot still answers (ungrounded) during early development.
"""
from sqlalchemy.orm import Session


async def retrieve(db: Session, query: str, crop: str | None = None, k: int = 5) -> list[dict]:
    # TODO: real pgvector similarity search. For now, no retrieval.
    return []
