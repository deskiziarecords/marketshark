import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class AnomalyReport:
    """Structured report for detected market anomalies."""
    score: float
    is_suspicious: bool
    threat_type: str  # STATIC, DYNAMIC, POLYMORPHIC
    lambda_impact: str
    details: Dict[str, float]  # Additional heuristic details

class MarketHeuristicEngine:
    """
    Upgraded Antivirus Heuristic Engine for OHLC data.
    Detects zero-day market threats using static and dynamic analysis.
    """

    def __init__(
        self,
        threshold: float = 70.0,
        static_weight: float = 0.7,
        dynamic_weight: float = 0.3,
        entropy_threshold: float = 0.85,
        volume_spike_multiplier: float = 3.0,
        wick_body_ratio: float = 3.0,
        body_ratio_threshold: float = 0.15,
    ):
        self.threshold = threshold
        self.static_weight = static_weight
        self.dynamic_weight = dynamic_weight
        self.entropy_threshold = entropy_threshold
        self.volume_spike_multiplier = volume_spike_multiplier
        self.wick_body_ratio = wick_body_ratio
        self.body_ratio_threshold = body_ratio_threshold
        self.sequence_sandbox = []

    def static_heuristic_score(self, candle: Dict[str, float], avg_vol: float) -> Tuple[float, Dict[str, float]]:
        """
        Static heuristics for candle structure analysis.
        Returns score and detailed breakdown.
        """
        score = 0.0
        details = {}

        # 1. Wick-to-Body Ratio (Stop Hunt Detection)
        wick_size = (candle['high'] - max(candle['open'], candle['close'])) + (
            min(candle['open'], candle['close']) - candle['low']
        )
        body_size = abs(candle['close'] - candle['open'])
        details['wick_body_ratio'] = wick_size / (body_size + 1e-9)

        if wick_size > (body_size * self.wick_body_ratio):
            score += 30
            details['stop_hunt'] = 30

        # 2. Volume Spike (Institutional Footprint)
        details['volume_ratio'] = candle['volume'] / (avg_vol + 1e-9)
        if candle['volume'] > (avg_vol * self.volume_spike_multiplier):
            score += 40
            details['volume_spike'] = 40

        # 3. Indecision/Compression (Entropy Buildup)
        total_range = candle['high'] - candle['low'] + 1e-9
        body_ratio = body_size / total_range
        details['body_ratio'] = body_ratio

        if body_ratio < self.body_ratio_threshold:
            score += 20
            details['indecision'] = 20

        # 4. Momentum Divergence (New Heuristic)
        momentum = (candle['close'] - candle['open']) / body_size if body_size > 0 else 0
        details['momentum'] = momentum
        if abs(momentum) < 0.1 and body_size > 0:
            score += 10
            details['momentum_divergence'] = 10

        return score, details

    def dynamic_heuristic_analysis(self, current_sequence: str) -> Tuple[float, Dict[str, float]]:
        """
        Dynamic heuristics using sequence entropy.
        Returns score and entropy details.
        """
        if not current_sequence or len(current_sequence) < 2:
            return 0.0, {'entropy': 0.0}

        chars = list(current_sequence)
        probs = [chars.count(c) / len(chars) for c in set(chars)]
        entropy = -sum(p * np.log2(p + 1e-9) for p in probs)
        details = {'entropy': entropy}

        return 100 if entropy > self.entropy_threshold else 0, details

    def analyze_tick(
        self,
        ohlc: Dict[str, float],
        avg_vol: float,
        sequence: str,
    ) -> AnomalyReport:
        """
        Analyze a single tick/OHLC candle and sequence.
        Returns an AnomalyReport with combined results.
        """
        static_score, static_details = self.static_heuristic_score(ohlc, avg_vol)
        dynamic_score, dynamic_details = self.dynamic_heuristic_analysis(sequence)

        total_score = (static_score * self.static_weight) + (dynamic_score * self.dynamic_weight)
        is_suspicious = total_score >= self.threshold
        threat_type = "POLYMORPHIC" if dynamic_score > 50 else "STATIC"

        # Expanded Lambda Impact Matrix
        if static_score > 60:
            lambda_impact = "λ7 CRITICAL"
        elif static_score > 40:
            lambda_impact = "λ6 VETO"
        elif dynamic_score > 80:
            lambda_impact = "λ5 DECEPTION"
        else:
            lambda_impact = "λ1 ENTRAPMENT"

        return AnomalyReport(
            score=round(total_score, 2),
            is_suspicious=is_suspicious,
            threat_type=threat_type,
            lambda_impact=lambda_impact,
            details={**static_details, **dynamic_details},
        )
