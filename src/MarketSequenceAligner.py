import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

@dataclass
class AlignmentResult:
    """Structured result for sequence alignment."""
    score: float
    alignment_str: str
    match_percentage: float
    homology_detected: bool
    aligned_query: str  # Aligned query sequence
    aligned_subject: str  # Aligned subject sequence

class MarketSequenceAligner:
    """
    Bio-Inspired Pattern Matching: Smith-Waterman Local Alignment for OHLC Sequences.
    Repurposes BLAST logic to find homologous market structures.
    """

    def __init__(
        self,
        match_score: int = 2,
        mismatch_penalty: int = -1,
        gap_penalty: int = -2,
        homology_threshold: float = 75.0
    ):
        self.match = match_score
        self.mismatch = mismatch_penalty
        self.gap = gap_penalty
        self.homology_threshold = homology_threshold
        # Symbol Scoring Matrix (Chess-inspired conviction levels)
        self.symbol_weights = {
            'B': 9,  # Bullish Breakout
            'I': 9,  # Institutional Accumulation
            'W': 5,  # Weak Bullish
            'w': 5,  # Weak Bearish
            'U': 3,  # Uncertain
            'D': 3,  # Distribution
            'X': 1   # Neutral/Noise
        }

    def align(self, query: str, subject: str) -> AlignmentResult:
        """
        Performs Local Sequence Alignment between query and subject.
        Returns alignment score, strings, and homology detection.
        """
        n, m = len(query), len(subject)
        if n == 0 or m == 0:
            raise ValueError("Query and subject sequences cannot be empty.")

        score_matrix = np.zeros((n + 1, m + 1))

        # Fill DP Matrix
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                # Calculate Match/Mismatch
                if query[i-1] == subject[j-1]:
                    score = self.match * self.symbol_weights.get(query[i-1], 1)
                else:
                    score = self.mismatch

                score_matrix[i, j] = max(
                    0,
                    score_matrix[i-1, j-1] + score,  # Match/Mismatch
                    score_matrix[i-1, j] + self.gap,  # Deletion
                    score_matrix[i, j-1] + self.gap   # Insertion
                )

        max_score = np.max(score_matrix)
        max_pos = np.unravel_index(np.argmax(score_matrix), score_matrix.shape)
        aligned_query, aligned_subject = self._traceback(score_matrix, query, subject, max_pos)

        # Normalize score for homology detection
        max_possible_score = min(n, m) * self.match * max(self.symbol_weights.values())
        match_pct = (max_score / max_possible_score) * 100 if max_possible_score > 0 else 0

        return AlignmentResult(
            score=max_score,
            alignment_str=f"Aligned_{max_pos[0]}_{max_pos[1]}",
            match_percentage=round(match_pct, 2),
            homology_detected=match_pct >= self.homology_threshold,
            aligned_query=aligned_query,
            aligned_subject=aligned_subject
        )

    def _traceback(
        self,
        matrix: np.ndarray,
        query: str,
        subject: str,
        start_pos: Tuple[int, int]
    ) -> Tuple[str, str]:
        """
        Traceback to generate aligned sequences.
        """
        i, j = start_pos
        aligned_q, aligned_s = [], []

        while i > 0 and j > 0 and matrix[i, j] != 0:
            current_score = matrix[i, j]
            diag_score = matrix[i-1, j-1]
            up_score = matrix[i-1, j]
            left_score = matrix[i, j-1]

            if current_score == diag_score + (
                self.match * self.symbol_weights.get(query[i-1], 1)
                if query[i-1] == subject[j-1]
                else self.mismatch
            ):
                aligned_q.append(query[i-1])
                aligned_s.append(subject[j-1])
                i -= 1
                j -= 1
            elif current_score == up_score + self.gap:
                aligned_q.append(query[i-1])
                aligned_s.append('-')
                i -= 1
            else:
                aligned_q.append('-')
                aligned_s.append(subject[j-1])
                j -= 1

        return ''.join(reversed(aligned_q)), ''.join(reversed(aligned_s))
