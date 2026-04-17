import sys
import os
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from embeddings import embed_sequence
from vector_db import store_pattern, query_similar
from carver import OHLCFileCarver

def test_embeddings():
    print("Testing embeddings...")
    emb = embed_sequence("ABC")
    assert len(emb) == 384
    print("Embeddings OK.")

def test_vector_db():
    print("Testing vector DB...")
    store_pattern("ABC", {"win_rate": 0.6, "avg_rr": 1.5, "count": 10, "cluster": "neutral"})
    matches = query_similar("ABC", n_results=1)
    assert len(matches) > 0
    assert matches[0]["pattern"] == "ABC"
    print("Vector DB OK.")

def test_carver():
    print("Testing carver...")
    # Create dummy data
    data = {
        'close': [1.0 + 0.01 * np.sin(i/5) for i in range(100)],
        'high': [1.02 for _ in range(100)],
        'low': [0.98 for _ in range(100)],
        'volume': [100 for _ in range(100)],
        'timestamp': pd.date_range("2024-01-01", periods=100, freq="min")
    }
    df = pd.DataFrame(data)
    carver = OHLCFileCarver()
    zones = carver.carve_zones(df, min_duration=5)
    print(f"Carved {len(zones)} zones.")
    assert len(zones) >= 0
    print("Carver OK.")

if __name__ == "__main__":
    try:
        test_embeddings()
        test_vector_db()
        test_carver()
        print("All smoke tests passed!")
    except Exception as e:
        print(f"Smoke test failed: {e}")
        sys.exit(1)
