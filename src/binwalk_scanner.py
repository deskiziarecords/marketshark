#!/usr/bin/env python3
"""
binwalk_scanner.py
Signature scanning + entropy analysis for hidden market structures.
Detects embedded patterns & distinguishes trending vs ranging regimes.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from scipy.stats import entropy

SIGNATURE_DB = {
    "BULL_FLAG": ["B","D","D","B"],
    "EVENING_STAR": ["I","X","W"],
    "ACCUMULATION_ZONE": ["W","X","X","U"],
    "LIQUIDITY_SWEEP": ["Z","W","C"],
    "FALSE_BREAKOUT": ["V","X","S"]
}

class MarketSignatureScanner:
    def __init__(self, window: int = 20):
        self.window = window
        self.signatures = SIGNATURE_DB

    def compute_entropy(self, series: pd.Series) -> float:
        """Shannon entropy on binned returns."""
        binned = pd.qcut(series.dropna(), q=5, labels=False, duplicates='drop')
        counts = binned.value_counts(normalize=True)
        return float(entropy(counts.values, base=2))

    def scan_signatures(self, df: pd.DataFrame) -> List[Dict]:
        if 'token' not in df.columns:
            raise ValueError("Requires 'token' column")
        
        tokens = df['token'].values
        matches = []

        for name, pattern in self.signatures.items():
            pat_len = len(pattern)
            for i in range(len(tokens) - pat_len + 1):
                if list(tokens[i:i+pat_len]) == pattern:
                    matches.append({
                        "offset": i,
                        "signature": name,
                        "timestamp": df.iloc[i]['timestamp'],
                        "entropy": self.compute_entropy(df.iloc[i:i+self.window]['close'].pct_change())
                    })
        return sorted(matches, key=lambda x: x['offset'])

    def regime_entropy_profile(self, df: pd.DataFrame, step: int = 50) -> pd.DataFrame:
        """Rolling entropy to detect compressed (ranging) vs chaotic (trending) phases."""
        returns = df['close'].pct_change()
        entropies = []
        for i in range(0, len(returns) - step, step):
            entropies.append(self.compute_entropy(returns.iloc[i:i+step]))
        return pd.DataFrame({"entropy": entropies}, index=df.index[:len(entropies)])

if __name__ == "__main__":
    df = pd.read_csv("data/eurusd_1min_tokenized.csv", parse_dates=["timestamp"])
    scanner = MarketSignatureScanner()
    sigs = scanner.scan_signatures(df)
    print(f"🔍 Found {len(sigs)} signature matches. Top: {sigs[:3]}")
