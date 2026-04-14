# Add this to the end of your existing mine_patterns.py

from vector_db import store_pattern

# Inside the pattern loop, after computing stats:
for pat, stats in pattern_db.items():
    if stats["count"] >= min_occurrences:
        win_rate = stats["win_count"] / stats["count"]
        metadata = {
            "length": len(pat),
            "count": stats["count"],
            "win_rate": round(win_rate, 3),
            "avg_pips": round(stats["total_pips"] / stats["count"], 2),
            "avg_rr": round(stats["avg_rr"], 2),
            "last_seen": stats["last_seen"],
            "cluster": "high" if win_rate > 0.7 else "low" if win_rate < 0.55 else "neutral"
        }
        # Store in ChromaDB with embedding
        store_pattern(pat, metadata)
