#!/usr/bin/env python3
"""
embeddings.py
Generates fixed-size embeddings for token sequences using a small, fast model.
Uses sentence-transformers with all-MiniLM-L6-v2 (~80MB, CPU-friendly).
"""
import numpy as np
from sentence_transformers import SentenceTransformer

# Load once at startup (cached)
_model = None

def get_model():
    global _model
    if _model is None:
        # Small, fast, CPU-optimized model
        _model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')
    return _model

def embed_sequence(token_seq: str, normalize=True) -> np.ndarray:
    """
    Convert token string (e.g., "DGZHI...") → 384-dim embedding
    """
    model = get_model()
    # Treat token sequence as a "sentence"
    embedding = model.encode([token_seq], convert_to_numpy=True)[0]
    if normalize:
        embedding = embedding / np.linalg.norm(embedding)
    return embedding.tolist()

def embed_batch(sequences: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = model.encode(sequences, convert_to_numpy=True, batch_size=32)
    return [emb / np.linalg.norm(emb) for emb in embeddings]
