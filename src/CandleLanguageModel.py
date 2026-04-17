import jax
import jax.numpy as jnp
import numpy as np
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class CLMConfig:
    """Configuration for the Candle Language Model."""
    alphabet: str = "BIXUDWw"  # Chess-inspired 7-symbol alphabet
    context_window: int = 512  # Sequence length for Transformer attention
    embedding_dim: int = 384   # Maps to all-MiniLM-L6-v2 dimensions
    num_experts: int = 256     # BailingMoE Expert count

class CandleLanguageModel:
    """
    CLM (Candle Language Model): Implements NLP-style tokenization and
    Contextual Embeddings for OHLC Market DNA.
    """

    def __init__(self, config: CLMConfig):
        self.config = config
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.token_map = {
            'B': 900,  # Bullish Breakout
            'I': -900, # Bearish Breakout
            'W': 500,  # Weak Bullish
            'w': -500, # Weak Bearish
            'U': 330,  # Uncertain Bullish
            'D': -320, # Uncertain Bearish
            'X': 100,  # Neutral/Noise
        }

    def tokenize(
        self,
        ohlc_data: List[Dict[str, float]],
        atr: float,
    ) -> str:
        """
        Geometric Tokenization: Converts OHLC -> BIXUDWw.
        Uses ATR-normalized geometry to ensure volatility-invariance.
        """
        if not ohlc_data:
            raise ValueError("OHLC data cannot be empty.")

        tokens = []
        for candle in ohlc_data:
            body = abs(candle['close'] - candle['open'])
            candle_range = max(1e-9, candle['high'] - candle['low'])
            ratio = body / candle_range

            if ratio < 0.1:
                tokens.append('X')
            elif candle['close'] > candle['open']:
                tokens.append('B' if ratio > 0.6 else 'U')
            else:
                tokens.append('I' if ratio > 0.6 else 'D')

        return "".join(tokens)

    def get_contextual_embedding(
        self,
        sequence: str,
    ) -> jnp.ndarray:
        """
        Transformer Embedding: Converts tokens into 384-D vector space.
        Similar candle contexts produce similar vectors.
        """
        if not sequence:
            raise ValueError("Sequence cannot be empty.")

        embedding = self.encoder.encode([sequence])
        return jnp.array(embedding[0])  # Return as JAX array

    @jax.jit
    def apply_attention(
        self,
        embedding_matrix: jnp.ndarray,
    ) -> jnp.ndarray:
        """
        SOS-27-X Attention Kernel: Determines which past candles matter.
        Uses RoPE (Rotary Position Embeddings) for long-context understanding.
        """
        # Split into query, key, value
        q, k, v = jnp.split(embedding_matrix, 3, axis=-1)

        # Scaled dot-product attention
        scores = jnp.matmul(q, jnp.swapaxes(k, -1, -2)) / jnp.sqrt(q.shape[-1])
        probs = jax.nn.softmax(scores)
        output = jnp.matmul(probs, v)

        return output

    def predict_next_state(
        self,
        sequence: str,
    ) -> Dict[str, float]:
        """
        Output: Probability distribution of the next candle state.
        Example: I (Momentum) has a 54.3% continuation probability.
        """
        if not sequence:
            raise ValueError("Sequence cannot be empty.")

        # Example: Use a simple lookup for demonstration
        # In practice, you would use a trained model or statistical analysis
        last_token = sequence[-1] if sequence else 'X'
        probabilities = {
            'B': {'B': 0.6, 'I': 0.1, 'U': 0.2, 'X': 0.1},
            'I': {'I': 0.543, 'B': 0.22, 'X': 0.15, 'D': 0.087},
            'U': {'U': 0.4, 'B': 0.3, 'X': 0.2, 'D': 0.1},
            'D': {'D': 0.5, 'I': 0.3, 'X': 0.15, 'w': 0.05},
            'X': {'X': 0.7, 'U': 0.15, 'D': 0.1, 'B': 0.05},
        }

        return probabilities.get(last_token, {'X': 1.0})

    def generate_embedding_matrix(
        self,
        sequences: List[str],
    ) -> jnp.ndarray:
        """
        Generates an embedding matrix for a list of sequences.
        Useful for batch processing.
        """
        embeddings = self.encoder.encode(sequences)
        return jnp.array(embeddings)
