#!/usr/bin/env python3
"""
timeline_clusterer.py
Multi-resolution temporal clustering of candle sequences & IPDA letters.
Prevents data overload by grouping patterns across zoom levels.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from collections import defaultdict

class TemporalClusterEngine:
    def __init__(self, zoom_levels: Dict[str, str] = None):
        self.zoom_levels = zoom_levels or {
            "micro": "1min",
            "meso": "15min",
            "macro": "1h"
        }

    def cluster_by_token_sequence(self, df: pd.DataFrame) -> Dict[str, List[dict]]:
        if 'token' not in df.columns:
            raise ValueError("DataFrame must contain 'token' column")
        
        results = defaultdict(list)
        current_seq = []
        current_start = None

        for i, row in df.iterrows():
            token = row['token']
            if current_start is None:
                current_start = i
                current_seq = [token]
                continue

            # Group if same token or follows logical sequence
            if token == current_seq[-1] or (token in "BDM" and current_seq[-1] in "BDM"):
                current_seq.append(token)
            else:
                results["clusters"].append({
                    "start_idx": current_start,
                    "end_idx": i-1,
                    "duration": i - current_start,
                    "sequence": "".join(current_seq),
                    "dominant_token": max(set(current_seq), key=current_seq.count)
                })
                current_start = i
                current_seq = [token]

        return dict(results)

    def multi_res_cluster(self, df: pd.DataFrame) -> Dict[str, List[dict]]:
        """Cluster across timeframes using resampling."""
        clusters = {}
        for level, tf in self.zoom_levels.items():
            resampled = df.resample(tf, on='timestamp').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum', 'token': lambda x: x.mode()[0] if len(x)>0 else 'N'
            }).dropna()
            clusters[level] = self.cluster_by_token_sequence(resampled)
        return clusters

if __name__ == "__main__":
    df = pd.read_csv("data/eurusd_1min_tokenized.csv", parse_dates=["timestamp"])
    engine = TemporalClusterEngine()
    clusters = engine.multi_res_cluster(df)
    print(f"📊 Micro clusters: {len(clusters['micro'].get('clusters', []))}")
