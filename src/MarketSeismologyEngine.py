import numpy as np
from scipy.signal import butter, filtfilt
from sklearn.cluster import DBSCAN
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class SeismicMarketEvent:
    """Structured result for seismic market events."""
    event_type: str  # P_WAVE, S_WAVE, SURFACE_WAVE, NOISE
    magnitude: float
    is_epicenter: bool
    status: str
    details: Optional[Dict] = None  # Additional event details

class MarketSeismologyEngine:
    """
    Seismology Waveform Analysis for Market Microstructure.
    Adapts SeisLM concepts to identify 'Market Earthquakes' (Breakouts).
    """

    def __init__(
        self,
        sample_rate: int = 1000,  # ms-level precision
        p_wave_threshold: float = 0.7,
        stasis_u_t: int = 1,
        dbscan_eps: float = 50,
        dbscan_min_samples: int = 5,
        s_wave_body_ratio: float = 0.75,
        phase_shift_displacement: float = 1.2,
        v_ratio_entrapment: float = 0.7,
    ):
        self.sample_rate = sample_rate
        self.p_wave_threshold = p_wave_threshold
        self.stasis_u_t = stasis_u_t
        self.dbscan_eps = dbscan_eps
        self.dbscan_min_samples = dbscan_min_samples
        self.s_wave_body_ratio = s_wave_body_ratio
        self.phase_shift_displacement = phase_shift_displacement
        self.v_ratio_entrapment = v_ratio_entrapment

    def _apply_lowpass_filter(self, data: np.ndarray) -> np.ndarray:
        """Removes stochastic noise to reveal structural waveforms (ALMA style)."""
        b, a = butter(3, 0.1, fs=self.sample_rate)
        return filtfilt(b, a, data)

    def detect_p_wave(
        self,
        tick_intervals: np.ndarray,
        price_levels: np.ndarray,
    ) -> bool:
        """
        P-wave Detection: Early institutional order flow.
        Identified via Tick Velocity Bursts and Burst Density.
        """
        if len(tick_intervals) != len(price_levels):
            raise ValueError("Tick intervals and price levels must have the same length.")

        # Cluster ticks in time-price space (DBSCAN)
        features = np.column_stack((tick_intervals, price_levels))
        db = DBSCAN(eps=self.dbscan_eps, min_samples=self.dbscan_min_samples).fit(features)

        # High burst density = P-Wave detection
        burst_density = np.sum(db.labels_ >= 0) / len(tick_intervals)
        return burst_density > self.p_wave_threshold

    def phase_pick(
        self,
        price_window: np.ndarray,
        v_ratio: float,
    ) -> str:
        """
        Phase Picking: Identifies the exact candle where trend 'phase' shifts.
        Uses λ1 Phase Entrapment decay logic.
        """
        if len(price_window) == 0:
            raise ValueError("Price window cannot be empty.")

        # Trigger if Price Variation / ATR20 < 0.7δ (Mathematical exhaustion)
        if v_ratio < self.v_ratio_entrapment:
            return "ENTRAPMENT_ZONE"  # Pre-quake stasis

        # Detect displacement magnitude
        displacement = np.abs(price_window[-1] - price_window)
        if np.any(displacement > self.phase_shift_displacement):
            return "PHASE_SHIFT"

        return "STABLE_NOISE"

    def analyze_waveform(
        self,
        tick_data: Dict[str, np.ndarray],
        l1_context: Dict[str, int],
    ) -> SeismicMarketEvent:
        """
        Main execution logic for 'Market Earthquake' classification.
        """
        # Validate inputs
        required_tick_keys = {'intervals', 'prices', 'body', 'range', 'volatility_impulse'}
        if not required_tick_keys.issubset(tick_data.keys()):
            raise ValueError(f"Tick data must contain keys: {required_tick_keys}")

        # 1. Detect P-Wave (Institutional Precursor)
        has_p_wave = self.detect_p_wave(tick_data['intervals'], tick_data['prices'])

        # 2. Monitor for S-Wave (Retail Follow-through / λ6 Displacement)
        body_ratio = tick_data['body'] / (tick_data['range'] + 1e-9)
        has_s_wave = body_ratio > self.s_wave_body_ratio

        # 3. Detect Surface Wave (Gamma Squeeze / Phase 2 Expansion)
        is_expanding = l1_context.get('sigma_t', 0) == 2 and has_s_wave

        details = {
            'has_p_wave': has_p_wave,
            'has_s_wave': has_s_wave,
            'body_ratio': body_ratio,
            'is_expanding': is_expanding,
        }

        if is_expanding:
            magnitude = np.exp(tick_data['volatility_impulse'])  # Non-linear amplification
            return SeismicMarketEvent(
                event_type="SURFACE_WAVE",
                magnitude=magnitude,
                is_epicenter=True,
                status="EXPANSION_CRITICAL",
                details=details,
            )
        elif has_p_wave:
            return SeismicMarketEvent(
                event_type="P_WAVE",
                magnitude=0.35,
                is_epicenter=False,
                status="INSTITUTIONAL_BURST",
                details=details,
            )

        return SeismicMarketEvent(
            event_type="NOISE",
            magnitude=0.0,
            is_epicenter=False,
            status="NOMINAL",
            details=details,
        )
