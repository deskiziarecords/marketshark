"""
bulk_extractor.py
Parallel, high-speed feature extraction from raw OHLC/tick streams.
Identifies micro-structural artifacts without full context parsing.
"""
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import Dict, List, Callable
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

class MarketFeatureExtractor:
    def __init__(self, n_jobs: int = -1):
        self.n_jobs = n_jobs
        self.features = {
            "round_number_cluster": self._detect_round_numbers,
            "volatility_spike": self._detect_vol_spikes,
            "rapid_oscillation": self._detect_rapid_flip,
            "sweep_through": self._detect_sweeps
        }

    @staticmethod
    def _detect_round_numbers(df_chunk: pd.DataFrame) -> pd.Series:
        return (df_chunk['close'] % 0.00100).abs() < 0.00005

    @staticmethod
    def _detect_vol_spikes(df_chunk: pd.DataFrame) -> pd.Series:
        vol_ma = df_chunk['volume'].rolling(20).mean()
        return df_chunk['volume'] > (vol_ma * 3.0)

    @staticmethod
    def _detect_rapid_flip(df_chunk: pd.DataFrame) -> pd.Series:
        if 'token' not in df_chunk.columns: return pd.Series(False, index=df_chunk.index)
        toks = df_chunk['token'].astype(str)
        return (toks.shift(1).isin(['Z','S']) & toks.isin(['V','W'])) | \
               (toks.shift(1).isin(['V','W']) & toks.isin(['Z','S']))

    @staticmethod
    def _detect_sweeps(df_chunk: pd.DataFrame) -> pd.Series:
        wicks = df_chunk['high'] - df_chunk['low']
        bodies = (df_chunk['close'] - df_chunk['open']).abs()
        return (wicks > 0) & (bodies / wicks) < 0.2

    def extract_chunk(self, args) -> Dict[str, pd.Series]:
        chunk_df, name = args
        return {name: feat(chunk_df) for name, feat in self.features.items()}

    def extract_parallel(self, df: pd.DataFrame, chunk_size: int = 50000) -> Dict[str, pd.Series]:
        chunks = [(df.iloc[i:i+chunk_size], f"chunk_{i}") for i in range(0, len(df), chunk_size)]
        results = defaultdict(list)
        
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            for chunk_res in executor.map(self.extract_chunk, chunks):
                for feat_name, series in chunk_res.items():
                    results[feat_name].append(series)
                    
        return {k: pd.concat(v) for k, v in results.items()}

if __name__ == "__main__":
    df = pd.read_csv("data/eurusd_1min_tokenized.csv", parse_dates=["timestamp"])
    extractor = MarketFeatureExtractor(n_jobs=4)
    features = extractor.extract_parallel(df)
    print(f"⚡ Extracted {len(features)} features. Vol spikes: {features['volatility_spike'].sum()}")
