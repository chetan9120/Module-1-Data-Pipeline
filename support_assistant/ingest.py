"""
Ingestion + embedding stage of the RAG pipeline.

Loads the 8 corpus documents from docs/, chunks them (one chunk per
document, since each document is already short and topically atomic),
embeds each chunk locally with sentence-transformers' all-MiniLM-L6-v2
(no API key, no network call beyond the one-time model download), and
stores the embeddings in a persistent ChromaDB collection called
"zepto_policies".

Run directly (`python ingest.py`) to (re)build the collection, or import
`get_or_build_collection()` from other modules (main.py / graph.py use this
on startup).
"""
import os
import glob

import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "zepto_policies"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def load_chunks() -> list[dict]:
    """One chunk per document file -- each doc_XX.txt is already a single
    short, topically atomic policy paragraph, so no further splitting is
    needed."""
    chunks = []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "doc_*.txt"))):
        doc_id = os.path.splitext(os.path.basename(path))[0]  # e.g. "doc_01"
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        chunks.append({"id": doc_id, "text": text})
    return chunks


def get_or_build_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    if collection.count() == 0:
        chunks = load_chunks()
        embedder = get_embedder()
        embeddings = embedder.encode([c["text"] for c in chunks]).tolist()
        collection.add(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            embeddings=embeddings,
        )
    return collection


def query_top_k(query: str, k: int = 3) -> list[dict]:
    """Embed `query` and retrieve the top-k most similar chunks (cosine
    similarity, ChromaDB's default distance space)."""
    collection = get_or_build_collection()
    embedder = get_embedder()
    query_embedding = embedder.encode([query]).tolist()
    result = collection.query(query_embeddings=query_embedding, n_results=k)

    hits = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    for doc_id, doc_text, dist in zip(ids, docs, distances):
        hits.append({"id": doc_id, "text": doc_text, "distance": dist})
    return hits


if __name__ == "__main__":
    col = get_or_build_collection()
    print(f"Collection '{COLLECTION_NAME}' ready with {col.count()} chunks.")
    for hit in query_top_k("Is standard delivery free?", k=3):
        print(hit["id"], round(hit["distance"], 4), hit["text"][:80])
