import chromadb
from chromadb.config import Settings
import os
from embeddings import embed_sequence

CHROMA_PATH = os.path.join(os.getcwd(), 'chroma_db')
COLLECTION_NAME = "eurusd_patterns"

def get_client():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))

def get_collection():
    client = get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

def store_pattern(pattern: str, meta: dict):
    collection = get_collection()
    collection.upsert(ids=[pattern], embeddings=[embed_sequence(pattern)], metadatas=[{**meta, "pattern": pattern}])

def query_similar(token_window: str, n_results: int = 5, min_win_rate: float = 0.0) -> list[dict]:
    collection = get_collection()
    results = collection.query(
        query_embeddings=[embed_sequence(token_window)],
        n_results=n_results * 2,
        where={"win_rate": {"$gte": min_win_rate}} if min_win_rate > 0 else None
    )
    matches = []
    if results.get('metadatas') and results['metadatas'][0]:
        for i, meta in enumerate(results['metadatas'][0]):
            sim = 1.0 - min(results['distances'][0][i], 1.0)
            matches.append({
                "pattern": meta["pattern"], "similarity": round(sim, 4),
                "win_rate": meta.get("win_rate", 0), "avg_rr": meta.get("avg_rr", 0),
                "count": meta.get("count", 0), "cluster": meta.get("cluster", "neutral")
            })
    matches.sort(key=lambda x: x["similarity"] * 0.6 + x["win_rate"] * 0.4, reverse=True)
    return matches[:n_results]#!/usr/bin/env python3
"""
vector_db.py
ChromaDB integration for pattern storage and similarity search.
Persistent, local, no server required.
"""
import chromadb
from chromadb.config import Settings
import os
from embeddings import embed_sequence

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "eurusd_patterns"

def get_client():
    return chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))

def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Cosine similarity for embeddings
    )

def store_pattern(pattern: str, meta dict):
    """
    Store a pattern with its embedding and metadata.
    metadata should include: win_rate, avg_rr, count, cluster, last_seen, etc.
    """
    collection = get_collection()
    embedding = embed_sequence(pattern)
    
    # Use pattern as ID (unique)
    collection.upsert(
        ids=[pattern],
        embeddings=[embedding],
        metadatas=[{**metadata, "pattern": pattern}]
    )

def query_similar(token_window: str, n_results=5, min_win_rate=0.0) -> list[dict]:
    """
    Find top-N similar patterns to the current token window.
    Returns list of pattern metadata sorted by similarity.
    """
    collection = get_collection()
    query_embedding = embed_sequence(token_window)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results * 2,  # Get more to filter
        where={"win_rate": {"$gte": min_win_rate}}  # Optional filter
    )
    
    # Format results
    matches = []
    if results['metadatas'] and results['metadatas'][0]:
        for i, meta in enumerate(results['metadatas'][0]):
            matches.append({
                "pattern": meta["pattern"],
                "similarity": 1 - (results['distances'][0][i] / 2),  # Convert cosine distance to similarity
                "win_rate": meta["win_rate"],
                "avg_rr": meta["avg_rr"],
                "count": meta["count"],
                "cluster": meta["cluster"]
            })
    
    # Re-rank by combined score: similarity * win_rate weight
    matches.sort(key=lambda x: x["similarity"] * 0.6 + x["win_rate"] * 0.4, reverse=True)
    return matches[:n_results]

def get_pattern_stats():
    collection = get_collection()
    count = collection.count()
    return {"total_patterns": count, "collection": COLLECTION_NAME}
