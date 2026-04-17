"""
carver.py
File carving for market structure: extracts hidden accumulation/distribution zones 
by treating support/resistance levels as "headers/footers".
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class CarvedZone:
    start_idx: int
    end_idx: int
    header_price: float
    footer_price: float
    duration_min: int
    volume_total: float
    price_range: float
    zone_type: str  # 'ACCUMULATION' | 'DISTRIBUTION' | 'RANGE'

class OHLCFileCarver:
    def __init__(self, header_threshold: float = 0.0005, footer_threshold: float = 0.0005):
        self.header_thresh = header_threshold
        self.footer_thresh = footer_threshold

    def _find_boundaries(self, df: pd.DataFrame) -> Tuple[List[int], List[int]]:
        """Identify header (support) and footer (resistance) candidates using local extrema."""
        prices = df['close'].values
        # Simple rolling min/max as boundary proxies
        roll = 20
        headers = np.where((prices < np.roll(prices, roll)) & (prices < np.roll(prices, -roll))[0]
        footers = np.where((prices > np.roll(prices, roll)) & (prices > np.roll(prices, -roll))[0]
        return headers.tolist(), footers.tolist()

    def carve_zones(self, df: pd.DataFrame, min_duration: int = 15) -> List[CarvedZone]:
        headers, footers = self._find_boundaries(df)
        zones = []
        i = h = f = 0

        while i < len(df) - min_duration:
            # Find nearest header (support)
            while h < len(headers) and headers[h] < i: h += 1
            if h >= len(headers): break
            start = headers[h]

            # Find nearest footer (resistance) after header
            while f < len(footers) and footers[f] <= start: f += 1
            if f >= len(footers): break
            end = footers[f]

            if end - start < min_duration:
                i += 1
                continue

            zone = CarvedZone(
                start_idx=start, end_idx=end,
                header_price=df.iloc[start]['close'],
                footer_price=df.iloc[end]['close'],
                duration_min=end - start,
                volume_total=df.iloc[start:end]['volume'].sum(),
                price_range=df.iloc[start:end]['high'].max() - df.iloc[start:end]['low'].min(),
                zone_type='ACCUMULATION' if df.iloc[start]['close'] < df.iloc[end]['close'] else 'DISTRIBUTION'
            )
            zones.append(zone)
            i = end + 1

        return zones

if __name__ == "__main__":
    df = pd.read_csv("data/eurusd_1min_tokenized.csv", parse_dates=["timestamp"])
    carver = OHLCFileCarver()
    zones = carver.carve_zones(df)
    print(f"🔪 Carved {len(zones)} zones. First: {zones[0] if zones else 'None'}")
