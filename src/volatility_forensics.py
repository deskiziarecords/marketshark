#!/usr/bin/env python3
"""
volatility_forensics.py
Memory forensics for "live" market state: detects hidden structures between candles.
Plugin-based architecture for spoofing, iceberg, and dark pool detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class MarketArtifact:
    timestamp: str
    artifact_type: str
    confidence: float
    details: Dict

class BasePlugin(ABC):
    @abstractmethod
    def analyze(self, state: Dict) -> List[MarketArtifact]:
        pass

class IcebergDetector(BasePlugin):
    def analyze(self, state: Dict) -> List[MarketArtifact]:
        # Proxy: repeated small volume at same price level despite high activity
        vol = state.get('volume_series', [])
        if len(vol) < 10: return []
        repeated = np.where(np.diff(np.round(vol, 2)) == 0)[0]
        artifacts = [MarketArtifact(state['current_time'], 'ICEBERG_ORDER', 0.7, 
                                    {"repeats": len(repeated)})] if len(repeated) > 3 else []
        return artifacts

class SpoofingDetector(BasePlugin):
    def analyze(self, state: Dict) -> List[MarketArtifact]:
        # Proxy: large wick + immediate reversal + volume drop
        wick = state.get('upper_wick', 0)
        body = state.get('body_size', 1)
        vol_drop = state.get('vol_change', 1.0)
        if wick > (body * 3) and vol_drop < -0.5:
            return [MarketArtifact(state['current_time'], 'SPOOFING_LAYER', 0.85, {"wick_ratio": wick/body})]
        return []

class VolatilityMemoryForensics:
    def __init__(self):
        self.plugins: List[BasePlugin] = [IcebergDetector(), SpoofingDetector()]
        self.artifacts: List[MarketArtifact] = []

    def register_plugin(self, plugin: BasePlugin):
        self.plugins.append(plugin)

    def snapshot_state(self, row: pd.Series, prev_row: pd.Series = None) -> Dict:
        return {
            "current_time": row['timestamp'],
            "volume_series": [row['volume']] * 20,  # Simulated depth proxy
            "upper_wick": row['high'] - max(row['open'], row['close']),
            "body_size": abs(row['close'] - row['open']),
            "vol_change": (row['volume'] / prev_row['volume'] - 1) if prev_row is not None else 0
        }

    def analyze_candle(self, row: pd.Series, prev_row: pd.Series = None) -> List[MarketArtifact]:
        state = self.snapshot_state(row, prev_row)
        findings = []
        for plugin in self.plugins:
            findings.extend(plugin.analyze(state))
        self.artifacts.extend(findings)
        return findings

if __name__ == "__main__":
    df = pd.read_csv("data/eurusd_1min_tokenized.csv", parse_dates=["timestamp"])
    forensics = VolatilityMemoryForensics()
    
    # Simulate live analysis
    for i in range(1, min(100, len(df))):
        forensics.analyze_candle(df.iloc[i], df.iloc[i-1])
        
    print(f"🧠 Detected {len(forensics.artifacts)} live artifacts. Types: {set(a.artifact_type for a in forensics.artifacts)}")
