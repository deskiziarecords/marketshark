import pandas as pd
import numpy as np
from collections import Counter
import itertools

def tokenize_candles(df, doji_thresh_pct=5.0):
    """
    Vectorized tokenization: OHLC → 1 letter per candle (A-Z)
    Adapts to 7 years of EUR/USD volatility using global percentiles.
    """
    # 1. Core geometry
    body = df['close'] - df['open']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    rng = df['high'] - df['low']
    rng = rng.replace(0, np.nan).ffill()  # Avoid div/zero on flat candles

    # 2. Normalized metrics [0, 1]
    body_ratio = body.abs() / rng
    upper_ratio = upper_wick / rng
    lower_ratio = lower_wick / rng

    # 3. Direction code: 0=Doji/Neutral, 1=Bull, 2=Bear
    is_doji = body_ratio < (doji_thresh_pct / 100)
    dir_code = np.where(is_doji, 0, np.where(body > 0, 1, 2))

    # 4. Quantize body strength & wick asymmetry (3 bins each)
    body_bins = np.nanpercentile(body_ratio, [33, 66])
    body_code = np.digitize(body_ratio, body_bins)

    wick_diff = upper_ratio - lower_ratio
    wick_bins = np.nanpercentile(wick_diff, [33, 66])
    wick_code = np.digitize(wick_diff, wick_bins)

    # 5. Composite index (0-26) → cap at 25 for A-Z
    idx = dir_code * 9 + body_code * 3 + wick_code
    idx = np.clip(idx, 0, 25)

    # 6. Map to letters
    df['token'] = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))[idx]
    return df

# -------------------------
# USAGE & PATTERN MINING
# -------------------------
if __name__ == "__main__":
    # Load 7-year 1-min data
    df = pd.read_csv("eurusd_1min_7y.csv", parse_dates=["timestamp"])
    df = tokenize_candles(df)

    # 🔤 Create continuous letter sequence (drops NaNs, keeps order)
    seq = df['token'].dropna().str.cat(sep='')
    print(f"Total tokens: {len(seq)}")

    # 🔍 Example: Find most common 3-letter patterns
    n = 3
    ngrams = [seq[i:i+n] for i in range(len(seq)-n+1)]
    top_patterns = Counter(ngrams).most_common(15)
    print("\n📊 Top 3-letter patterns:")
    for pat, cnt in top_patterns:
        print(f"{pat}: {cnt}")

    # 📦 Save for embedding pipeline
    df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'token']].to_csv(
        "eurusd_1min_tokenized.csv", index=False
    )
