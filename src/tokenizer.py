import numpy as np
import pandas as pd

def tokenize_candle(open_p, high_p, low_p, close_p, doji_thresh_pct=5.0):
    """
    Tokenizes a single candle into a letter (A-Z).
    Based on geometry: Direction (3) x Body Strength (3) x Wick Asymmetry (3).
    Total 27 states, clipped to 26 (A-Z).
    """
    body = close_p - open_p
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    rng = high_p - low_p
    
    if rng == 0:
        return "A" # Default for flat candle
        
    body_ratio = abs(body) / rng
    upper_ratio = upper_wick / rng
    lower_ratio = lower_wick / rng
    
    # 1. Direction: 0=Doji/Neutral, 1=Bull, 2=Bear
    if body_ratio < (doji_thresh_pct / 100):
        dir_code = 0
    elif body > 0:
        dir_code = 1
    else:
        dir_code = 2
        
    # 2. Body strength (3 bins)
    if body_ratio < 0.33:
        body_code = 0
    elif body_ratio < 0.66:
        body_code = 1
    else:
        body_code = 2
        
    # 3. Wick Asymmetry (3 bins)
    wick_diff = upper_ratio - lower_ratio
    if wick_diff < -0.33:
        wick_code = 0
    elif wick_diff < 0.33:
        wick_code = 1
    else:
        wick_code = 2
        
    idx = dir_code * 9 + body_code * 3 + wick_code
    idx = int(np.clip(idx, 0, 25))
    
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx]

def tokenize_stream(df, doji_thresh_pct=5.0):
    """
    Vectorized tokenization for a dataframe.
    """
    body = df['close'] - df['open']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    rng = df['high'] - df['low'].replace(0, 1e-9) # Avoid div by zero
    
    body_ratio = body.abs() / rng
    upper_ratio = upper_wick / rng
    lower_ratio = lower_wick / rng
    
    is_doji = body_ratio < (doji_thresh_pct / 100)
    dir_code = np.where(is_doji, 0, np.where(body > 0, 1, 2))
    
    body_code = np.where(body_ratio < 0.33, 0, np.where(body_ratio < 0.66, 1, 2))
    
    wick_diff = upper_ratio - lower_ratio
    wick_code = np.where(wick_diff < -0.33, 0, np.where(wick_diff < 0.33, 1, 2))
    
    idx = dir_code * 9 + body_code * 3 + wick_code
    idx = np.clip(idx, 0, 25).astype(int)
    
    letters = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    return [letters[i] for i in idx]
