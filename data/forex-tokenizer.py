import pandas as pd
import numpy as np
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

def tokenize_1min_forex(df, atr_period=20, neutral_atr_mult=0.15):
    """
    Vectorized tokenization: 1-min OHLC → A-Z
    Uses ATR normalization for volatility regime invariance.
    """
    # 1. True Range & ATR
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()

    # 2. Candle geometry
    body = df['close'] - df['open']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']

    # 3. ATR-normalized features
    norm_body = body / atr
    norm_wick_diff = (upper_wick - lower_wick) / atr
    body_strength = body.abs() / atr

    # 4. Quantize to 3 bins each
    # Direction: -1 (bear), 0 (neutral), 1 (bull)
    dir_code = np.where(
        norm_body.abs() < neutral_atr_mult, 0,
        np.where(norm_body > 0, 1, -1)
    )

    # Strength: 0=small, 1=medium, 2=large
    str_edges = np.nanpercentile(body_strength, [33, 66])
    str_code = np.digitize(body_strength, str_edges)

    # Wick Asymmetry: -1=lower dominant, 0=balanced, 1=upper dominant
    wick_edges = np.nanpercentile(norm_wick_diff, [33, 66])
    wick_code = np.digitize(norm_wick_diff, wick_edges) - 1

    # 5. Composite index (3×3×3 = 27 → clip to 26 for A-Z)
    dir_idx = dir_code + 1
    wick_idx = wick_code + 1
    idx = dir_idx * 9 + str_code * 3 + wick_idx
    idx = np.clip(idx, 0, 25)

    # 6. Map to letters
    df['token'] = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))[idx]
    return df

# -------------------------
# DECODER & PATTERN MINING
# -------------------------
LETTER_MAP = {
    'A': 'Neutral/Small/Balanced', 'B': 'Neutral/Small/Lower', 'C': 'Neutral/Small/Upper',
    'D': 'Bull/Small/Balanced',    'E': 'Bull/Small/Lower',    'F': 'Bull/Small/Upper',
    'G': 'Bear/Small/Balanced',    'H': 'Bear/Small/Lower',    'I': 'Bear/Small/Upper',
    'J': 'Neutral/Med/Balanced',   'K': 'Neutral/Med/Lower',   'L': 'Neutral/Med/Upper',
    'M': 'Bull/Med/Balanced',      'N': 'Bull/Med/Lower',      'O': 'Bull/Med/Upper',
    'P': 'Bear/Med/Balanced',      'Q': 'Bear/Med/Lower',      'R': 'Bear/Med/Upper',
    'S': 'Neutral/Large/Balanced', 'T': 'Neutral/Large/Lower', 'U': 'Neutral/Large/Upper',
    'V': 'Bull/Large/Balanced',    'W': 'Bull/Large/Lower',    'X': 'Bull/Large/Upper',
    'Y': 'Bear/Large/Balanced',    'Z': 'Bear/Large/Lower'     # (Y/Z adjusted for 26 cap)
}

# -------------------------
# CHUNKED PROCESSING (7-YEAR SAFE)
# -------------------------
if __name__ == "__main__":
    INPUT_CSV = "eurusd_1min_7y.csv"
    OUTPUT_CSV = "eurusd_1min_tokenized.csv"
    CHUNK_SIZE = 500_000  # ~2-3 months per chunk

    tokens_seq = []
    first_chunk = True

    for chunk in pd.read_csv(INPUT_CSV, chunksize=CHUNK_SIZE, parse_dates=["timestamp"]):
        # Clean & sort
        chunk = chunk.sort_values("timestamp").reset_index(drop=True)
        
        # Tokenize
        chunk = tokenize_1min_forex(chunk)
        
        # Save chunk (overwrite header on first)
        mode = 'w' if first_chunk else 'a'
        header = first_chunk
        chunk.to_csv(OUTPUT_CSV, mode=mode, header=header, index=False)
        
        # Collect letters for sequence modeling
        tokens_seq.extend(chunk['token'].dropna().tolist())
        first_chunk = False

    #  Create continuous sequence
    seq = "".join(tokens_seq)
    print(f" Total tokens: {len(seq)}")

    #  Mine top 3-letter patterns (n-grams)
    n = 3
    ngrams = [seq[i:i+n] for i in range(len(seq)-n+1)]
    top_patterns = Counter(ngrams).most_common(10)
    print("\n Top 3-letter patterns:")
    for pat, cnt in top_patterns:
        meaning = " + ".join([LETTER_MAP.get(c, "?") for c in pat])
        print(f"{pat}: {cnt:,} → {meaning}")
