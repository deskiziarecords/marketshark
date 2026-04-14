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
import os, sys, pandas as pd
from collections import defaultdict
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from vector_db import store_pattern

def run(csv_path):
    print(" Loading CSV...")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df["fwd_pips"] = [(df.iloc[i+5]["close"]-df.iloc[i]["close"])/0.0001 if i+5<len(df) else float('nan') for i in range(len(df))]
    tokens = df["token"].fillna("").str.cat()
    db = defaultdict(lambda: {"count":0, "wins":0, "total_rr":0.0})
    
    print(" Mining patterns...")
    for w in [3,5,7]:
        for i in range(len(tokens)-w):
            pat, ret = tokens[i:i+w], df.iloc[i+w]["fwd_pips"]
            if pd.isna(ret): continue
            db[pat]["count"] += 1
            if ret > 0: db[pat]["wins"] += 1
            db[pat]["total_rr"] += (2.0 if ret>=16 else (-1.0 if ret<=-8 else ret/8))
            
    print(" Indexing ChromaDB...")
    cnt = 0
    for pat, s in db.items():
        if s["count"] >= 10:
            wr = s["wins"]/s["count"]
            store_pattern(pat, {"length":len(pat), "count":s["count"], "win_rate":round(wr,3), "avg_rr":round(s["total_rr"]/s["count"],2), "cluster":"high" if wr>0.7 else ("low" if wr<0.55 else "neutral")})
            cnt += 1
    print(f" Indexed {cnt} patterns. Ready.")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv)>1 else "data/eurusd_1min_tokenized.csv")
