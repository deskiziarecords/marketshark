import numpy as np
import scipy.signal as signal
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class RhythmTelemetry:
    """Structured result for market rhythm analysis."""
    tempo_bpm: float  # Price swings per window
    is_harmonic: bool  # Multi-timeframe alignment
    spectral_density: np.ndarray  # Spectrogram data
    fingerprint_hash: str  # Unique pattern identifier
    status: str  # Current rhythm status
    beat_locations: Optional[np.ndarray] = None  # Indices of detected beats

class MarketRhythmEngine:
    """
    Music Information Retrieval (MIR) for OHLC: Treats price action as a digital audio signal.
    Integrates λ3 Spectral Inversion and IPDA 'Beat' Detection.
    """

    def __init__(
        self,
        sample_rate: int = 128,
        lookback: int = 64,
        beat_threshold: float = 1.5,
        spectral_peak_threshold: float = 2.0,
    ):
        self.fs = sample_rate
        self.lookback = lookback
        self.beat_threshold = beat_threshold
        self.spectral_peak_threshold = spectral_peak_threshold

    def to_waveform(self, prices: np.ndarray) -> np.ndarray:
        """Converts price changes to amplitude 'audio' samples."""
        if len(prices) < 2:
            raise ValueError("Prices array must have at least 2 elements.")

        price_diff = np.diff(prices)
        return price_diff / (np.std(price_diff) + 1e-9)

    def compute_market_spectrogram(self, waveform: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generates a price-frequency heatmap (Time-Frequency Domain)."""
        if len(waveform) < self.lookback:
            raise ValueError(f"Waveform must be at least {self.lookback} samples long.")

        f, t, Sxx = signal.spectrogram(waveform, fs=self.fs, nperseg=self.lookback)
        return f, t, Sxx

    def detect_beats(
        self,
        prices_high: np.ndarray,
        prices_low: np.ndarray,
    ) -> Dict[str, float]:
        """
        Detects 'Beats' using Swing High/Low logic.
        Maps to 'Tempo' of the current market regime.
        """
        if len(prices_high) < 3 or len(prices_low) < 3:
            raise ValueError("High and low price arrays must have at least 3 elements.")

        swings_h = (prices_high[1:-1] > prices_high[:-2]) & (prices_high[1:-1] > prices_high[2:])
        swings_l = (prices_low[1:-1] < prices_low[:-2]) & (prices_low[1:-1] < prices_low[2:])

        tempo = (np.sum(swings_h) + np.sum(swings_l)) / (len(prices_high) / self.fs)
        beat_locations = np.where(swings_h | swings_l)[0] + 1  # +1 to adjust for slicing

        return {"tempo": tempo, "beat_locations": beat_locations}

    def check_harmony(
        self,
        phi_l1: float,
        waveform: np.ndarray,
    ) -> bool:
        """
        Chord Recognition: Validates if High-Frequency (L5) is in harmony with Macro (L1).
        Implementation of λ3 Spectral Inversion.
        """
        fft_data = np.fft.rfft(waveform)
        if len(fft_data) < 2:
            raise ValueError("Waveform FFT must have at least 2 elements.")

        # Find the dominant frequency's phase
        dominant_freq_idx = np.argmax(np.abs(fft_data[1:])) + 1
        phi_l5 = np.angle(fft_data[dominant_freq_idx])

        # Harmony is achieved if phase difference < π/2
        phase_diff = np.abs(phi_l5 - phi_l1)
        return phase_diff < (np.pi / 2)

    def generate_fingerprint(self, spectrogram: np.ndarray) -> str:
        """Shazam-style hashing: Identifies pattern DNA via spectrogram peaks."""
        if spectrogram.size == 0:
            raise ValueError("Spectrogram cannot be empty.")

        # Find local peaks in the spectrogram
        mean_spec = np.mean(spectrogram)
        std_spec = np.std(spectrogram)
        peaks = spectrogram > (mean_spec + self.spectral_peak_threshold * std_spec)

        # Simple hash of the peak bitmask
        return str(hash(peaks.tobytes()))

    def analyze(
        self,
        ohlcv: Dict[str, np.ndarray],
        l1_bias_phi: float,
    ) -> RhythmTelemetry:
        """
        Main analysis method: Computes rhythm telemetry for the given OHLCV data.
        """
        required_keys = {'close', 'high', 'low'}
        if not required_keys.issubset(ohlcv.keys()):
            raise ValueError(f"OHLCV data must contain keys: {required_keys}")

        waveform = self.to_waveform(ohlcv['close'])
        f, t, spec = self.compute_market_spectrogram(waveform)
        beats = self.detect_beats(ohlcv['high'], ohlcv['low'])
        in_harmony = self.check_harmony(l1_bias_phi, waveform)
        m_hash = self.generate_fingerprint(spec)

        status = "IN_HARMONY" if in_harmony else "DISSONANT: λ3 VETO"

        return RhythmTelemetry(
            tempo_bpm=beats['tempo'],
            is_harmonic=in_harmony,
            spectral_density=spec,
            fingerprint_hash=m_hash,
            status=status,
            beat_locations=beats['beat_locations'],
        )
