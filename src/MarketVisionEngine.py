import numpy as np
from scipy.signal import argrelextrema
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class KeypointDescriptor:
    """Structured representation of a market keypoint."""
    location: Tuple[int, float]  # (Time_Index, Price)
    scale: float                  # ATR-normalized scale
    orientation: float            # Trend Angle (arctan)
    descriptor: np.ndarray        # 16-bin movement histogram
    conviction: float             # Rarity/Strength score

class MarketVisionEngine:
    """
    CV-to-OHLC Adaptation: Detects Scale-Invariant Keypoints (SIFT/ORB).
    Identifies 'Structural Decision Nodes' that remain valid across timeframes.
    """

    def __init__(
        self,
        neighborhood_size: int = 16,
        descriptor_length: int = 16,
        match_threshold: float = 0.85,
    ):
        self.neighborhood = neighborhood_size
        self.descriptor_length = descriptor_length
        self.match_threshold = match_threshold
        self.feature_db = []  # Local descriptor memory

    def detect_keypoints(
        self,
        prices: np.ndarray,
        atr: np.ndarray,
    ) -> List[KeypointDescriptor]:
        """
        Detects local maxima/minima and calculates SIFT-inspired descriptors.
        """
        if len(prices) < 3 or len(atr) < 3:
            raise ValueError("Prices and ATR arrays must have at least 3 elements.")

        # 1. Keypoint Localization: Find local peaks and valleys
        maxima = argrelextrema(prices, np.greater)[0]
        minima = argrelextrema(prices, np.less)[0]
        candidates = np.sort(np.concatenate([maxima, minima]))

        keypoints = []
        for idx in candidates:
            if idx < self.neighborhood or idx > len(prices) - self.neighborhood:
                continue

            # 2. Scale Calculation (ATR-Invariant)
            scale = atr[idx]

            # 3. Orientation Assignment (Trend Angle)
            delta_p = prices[idx] - prices[idx - 1]
            orientation = np.arctan2(delta_p, 1)

            # 4. Descriptor Extraction: 16-candle local movement histogram
            start_idx = max(0, idx - self.descriptor_length // 2)
            end_idx = min(len(prices), idx + self.descriptor_length // 2)
            surrounding = prices[start_idx:end_idx]
            diffs = np.diff(surrounding)

            # Normalize diffs by local scale (ATR) to ensure scale invariance
            norm_diffs = diffs / (scale + 1e-9)

            # Binary Descriptor (ORB Style): 1 if price increased, 0 if decreased
            descriptor = (norm_diffs > 0).astype(int)

            # Pad or truncate descriptor to fixed length
            if len(descriptor) < self.descriptor_length:
                descriptor = np.pad(
                    descriptor,
                    (0, self.descriptor_length - len(descriptor)),
                    mode='constant',
                )
            elif len(descriptor) > self.descriptor_length:
                descriptor = descriptor[:self.descriptor_length]

            keypoints.append(KeypointDescriptor(
                location=(idx, prices[idx]),
                scale=scale,
                orientation=orientation,
                descriptor=descriptor,
                conviction=abs(delta_p / scale),
            ))

        return keypoints

    def match_features(
        self,
        query_descriptors: List[np.ndarray],
        historical_db: List[np.ndarray],
    ) -> List[float]:
        """
        Brute-force Hamming distance matching for binary ORB descriptors.
        Matches current 'Market DNA' against historical homologs.
        """
        matches = []
        for q in query_descriptors:
            for h in historical_db:
                if len(q) != len(h):
                    continue  # Skip mismatched descriptor lengths

                # Calculate Similarity (1 - Hamming Distance)
                similarity = np.mean(q == h)
                if similarity > self.match_threshold:
                    matches.append(similarity)

        return matches

    def update_feature_db(
        self,
        descriptors: List[np.ndarray],
    ) -> None:
        """Adds new descriptors to the historical database."""
        self.feature_db.extend(descriptors)
