#!/usr/bin/env python3
"""
Dukascopy Historical Data Fetcher CLI
Fetches tick data, aggregates to 1-min OHLCV, exports to CSV.
"""
import argparse
import lzma
import struct
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import sys
import os

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
VALID_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF", "EURGBP", "EURJPY", "GBPJPY"}

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch historical Forex data from Dukascopy")
    parser.add_argument("--symbol", required=True, help=f"Pair (e.g., EURUSD). Available: {', '.join(sorted(VALID_SYMBOLS))}")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--output", default="dukascopy_data.csv", help="Output CSV path")
    parser.add_argument("--resume", action="store_true", help="Skip already fetched dates")
    parser.add_argument("--verbose", action="store_true", help="Show download URLs & errors")
    return parser.parse_args()

def get_hour_range(start, end):
    """Generate list of datetime objects for each hour in range"""
    hours = []
    curr = start
    while curr <= end:
        hours.append(curr)
        curr += timedelta(hours=1)
    return hours

def fetch_tick_bytes(symbol, dt):
    """Download and decompress 1 hour of tick data"""
    year = dt.year
    month = dt.month - 1  # Dukascopy uses 0-indexed months
    day = dt.day
    hour = dt.hour
    url = f"{BASE_URL}/{symbol}/{year}/{month:02d}/{day:02d}/{hour}h_ticks.bi5"
    
    try:
        resp = requests.get(url, timeout=15, stream=True)
        if resp.status_code == 200 and len(resp.content) > 0:
            return lzma.decompress(resp.content)
    except Exception as e:
        if args.verbose:
            print(f"[WARN] Failed {url}: {e}", file=sys.stderr)
    return b""

def parse_ticks_to_df(binary, date):
    """Parse 20-byte tick records into DataFrame"""
    if len(binary) == 0:
        return pd.DataFrame()
        
    # Format: >Iffff (big-endian, 20 bytes per tick)
    # timestamp: uint32 (seconds since midnight UTC)
    # ask, bid, ask_vol, bid_vol: float32
    size = 20
    count = len(binary) // size
    fmt = '>Iffff'
    
    ts_list, price_list = [], []
    for i in range(count):
        chunk = binary[i*size:(i+1)*size]
        ts_sec, ask, bid, _, _ = struct.unpack(fmt, chunk)
        # Mid price
        mid = (ask + bid) / 2.0
        # Reconstruct full UTC datetime
        full_dt = date + timedelta(seconds=ts_sec)
        ts_list.append(full_dt)
        price_list.append(mid)
        
    df = pd.DataFrame({"timestamp": ts_list, "price": price_list})
    return df.set_index("timestamp")

def aggregate_to_1min(df):
    """Resample tick data to 1-min OHLCV"""
    if df.empty:
        return pd.DataFrame()
        
    ohlcv = df["price"].resample("1min").ohlc()
    ohlcv["volume"] = df["price"].resample("1min").count()
    ohlcv = ohlcv.dropna(subset=["open"])  # Remove minutes with no ticks
    return ohlcv.reset_index()

def main():
    global args
    args = parse_args()
    
    if args.symbol.upper() not in VALID_SYMBOLS:
        print(f"[ERROR] Symbol must be one of: {', '.join(sorted(VALID_SYMBOLS))}")
        sys.exit(1)
        
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d") + timedelta(hours=23)  # Include full end day
    hours = get_hour_range(start, end)
    
    print(f" Fetching {args.symbol} | {args.start} → {args.end} ({len(hours)} hours)")
    
    # Check resume
    existing_dates = set()
    if args.resume and os.path.exists(args.output):
        try:
            df_exist = pd.read_csv(args.output, parse_dates=["timestamp"])
            existing_dates = set(df_exist["timestamp"].dt.date.astype(str))
            print(f"📖 Resuming: {len(existing_dates)} days already fetched")
        except: pass

    hours_to_fetch = [h for h in hours if h.date().strftime("%Y-%m-%d") not in existing_dates]
    if not hours_to_fetch:
        print(" All dates already fetched. Nothing to do.")
        return

    all_frames = []
    total = len(hours_to_fetch)
    for i, dt in enumerate(hours_to_fetch):
        date_str = dt.strftime("%Y-%m-%d")
        print(f"\r [{i+1}/{total}] {date_str} {dt.hour:02d}:00", end="", flush=True)
        
        raw = fetch_tick_bytes(args.symbol, dt)
        if raw:
            tick_df = parse_ticks_to_df(raw, dt.date())
            min_df = aggregate_to_1min(tick_df)
            if not min_df.empty:
                all_frames.append(min_df)
                
        time.sleep(0.15)  # Polite rate limit
        
    print("\n🔧 Aggregating & saving...")
    if all_frames:
        full = pd.concat(all_frames).sort_values("timestamp").reset_index(drop=True)
        # Format to match your CSV spec
        full["timestamp"] = full["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
        full.rename(columns={"open":"open","high":"high","low":"low","close":"close","volume":"volume"}, inplace=True)
        full = full[["timestamp","open","high","low","close","volume"]]
        
        # Append or overwrite
        mode = "a" if args.resume and os.path.exists(args.output) else "w"
        header = not (args.resume and os.path.exists(args.output))
        full.to_csv(args.output, mode=mode, index=False, header=header)
        print(f" Saved {len(full)} candles to {args.output}")
    else:
        print(" No data found. Check symbol/dates or try different range.")

if __name__ == "__main__":
    main()
