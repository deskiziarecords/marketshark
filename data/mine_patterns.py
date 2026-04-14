#!/usr/bin/env python3
"""mine_patterns.py - Scans CSV, builds ChromaDB index"""
import os
import sys
import pandas as pd
from collections import defaultdict

# 🔑 FIX: Make 'src/' visible to Python
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from vector_db import store_pattern

def run(csv_path):
    print("📖 Loading CSV...")
    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        sys.exit(1)
        
    df = pd.read_csv(csv_path, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    # Calculate 5-bar forward return in pips
    df["fwd_pips"] = [
        (df.iloc[i+5]["close"] - df.iloc[i]["close"]) / 0.0001 if i+5 < len(df) else float('nan') 
        for i in range(len(df))
    ]
    
    tokens = df["token"].fillna("").str.cat()
    db = defaultdict(lambda: {"count": 0, "wins": 0, "total_rr": 0.0})
    
    print("⛏️ Mining patterns (3, 5, 7-length windows)...")
    for w in [3, 5, 7]:
        for i in range(len(tokens) - w):
            pat = tokens[i:i+w]
            ret = df.iloc[i+w]["fwd_pips"]
            if pd.isna(ret): continue
            
            db[pat]["count"] += 1
            if ret > 0: db[pat]["wins"] += 1
            # RR approximation: 8 pip SL, 16 pip TP
            db[pat]["total_rr"] += (2.0 if ret >= 16 else (-1.0 if ret <= -8 else ret / 8))
            
    print("💾 Indexing ChromaDB...")
    cnt = 0
    for pat, s in db.items():
        if s["count"] >= 10:  # Minimum occurrence filter
            wr = s["wins"] / s["count"]
            store_pattern(pat, {
                "length": len(pat),
                "count": s["count"],
                "win_rate": round(wr, 3),
                "avg_rr": round(s["total_rr"] / s["count"], 2),
                "cluster": "high" if wr > 0.7 else ("low" if wr < 0.55 else "neutral")
            })
            cnt += 1
    print(f"✅ Indexed {cnt} patterns into local VectorDB. Ready for MarketShark.")

if __name__ == "__main__":
    # Default to data/ folder, or use CLI arg
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/eurusd_1min_tokenized.csv"
    run(csv_file)
