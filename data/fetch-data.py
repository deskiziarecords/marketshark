#!/usr/bin/env python3
"""
Refined Forex Data Fetcher from Dukascopy
Optimized for data analysis and backtesting.
"""

import argparse
import sys
from datetime import datetime, timedelta
import pandas as pd

# Try to import dukascopy
try:
    from dukascopy_python import (
        fetch, 
        INTERVAL_MIN_1, INTERVAL_MIN_5, INTERVAL_MIN_15, INTERVAL_MIN_30,
        INTERVAL_HOUR_1, INTERVAL_HOUR_4, INTERVAL_DAY_1,
        OFFER_SIDE_BID
    )
    from dukascopy_python.instruments import (
        INSTRUMENT_FX_MAJORS_EUR_USD,
        INSTRUMENT_FX_MAJORS_GBP_USD,
        INSTRUMENT_FX_MAJORS_USD_JPY,
        INSTRUMENT_FX_MAJORS_AUD_USD,
        INSTRUMENT_FX_MAJORS_USD_CHF,
        INSTRUMENT_FX_MAJORS_USD_CAD,
        INSTRUMENT_FX_MAJORS_NZD_USD,
    )
    DUKASCOPY_OK = True
except ImportError:
    print(" Error: dukascopy-python not found.")
    print("   Install with: pip install dukascopy-python")
    DUKASCOPY_OK = False

# Mapping
INSTRUMENT_MAP = {
    'EUR_USD': INSTRUMENT_FX_MAJORS_EUR_USD,
    'GBP_USD': INSTRUMENT_FX_MAJORS_GBP_USD,
    'USD_JPY': INSTRUMENT_FX_MAJORS_USD_JPY,
    'AUD_USD': INSTRUMENT_FX_MAJORS_AUD_USD,
    'USD_CHF': INSTRUMENT_FX_MAJORS_USD_CHF,
    'USD_CAD': INSTRUMENT_FX_MAJORS_USD_CAD,
    'NZD_USD': INSTRUMENT_FX_MAJORS_NZD_USD,
}

INTERVAL_MAP = {
    '1m': INTERVAL_MIN_1,
    '5m': INTERVAL_MIN_5,
    '15m': INTERVAL_MIN_15,
    '30m': INTERVAL_MIN_30,
    '1h': INTERVAL_HOUR_1,
    '4h': INTERVAL_HOUR_4,
    '1d': INTERVAL_DAY_1,
}

def fetch_forex_data(asset='EUR_USD', timeframe='1h', days=30):
    if not DUKASCOPY_OK:
        return None
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    print(f" Fetching {asset} ({timeframe}) | Period: {days} days")
    
    try:
        # Fetch data
        df = fetch(
            instrument=INSTRUMENT_MAP[asset],
            interval=INTERVAL_MAP[timeframe],
            offer_side=OFFER_SIDE_BID,
            start=start,
            end=end,
        )

        if df is None or df.empty:
            print(" No data returned from Dukascopy.")
            return None

        # 1. Ensure Index is Datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 2. Timezone Correction (Dukascopy is GMT)
        # Most traders use UTC or New York time. Let's keep it UTC for clean analysis.
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')

        # 3. Clean OHLC Column Names (Dukascopy sometimes returns capitalized/lower mixed)
        df.columns = [c.capitalize() for c in df.columns]

        # 4. Remove empty weekend candles (where volume is 0)
        if 'Volume' in df.columns:
            df = df[df['Volume'] > 0]

        # 5. Move index to 'Timestamp' column for CSV friendliness
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Timestamp'}, inplace=True)
        
        print(f" Success! {len(df)} candles retrieved.")
        return df
        
    except Exception as e:
        print(f" Critical Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Dukascopy Forex Downloader')
    parser.add_argument('-a', '--asset', default='EUR_USD', choices=INSTRUMENT_MAP.keys())
    parser.add_argument('-t', '--timeframe', default='1h', choices=INTERVAL_MAP.keys())
    parser.add_argument('-d', '--days', type=int, default=30)
    parser.add_argument('-o', '--output', default=None)
    
    args = parser.parse_args()
    
    # Run fetcher
    df = fetch_forex_data(args.asset, args.timeframe, args.days)
    
    if df is not None:
        output_file = args.output if args.output else f"{args.asset}_{args.timeframe}.csv"
        # index=False ensures we don't get that "Unnamed: 0" column later
        df.to_csv(output_file, index=False)
        print(f" Data saved to {output_file}")
        print(df.head())
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()