#!/usr/bin/env python3
"""
Simple Forex Data Fetcher from Dukascopy
Handles the actual data structure correctly
"""

import argparse
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
except ImportError as e:
    print(f"❌ Error: {e}")
    print("   Install with: pip install dukascopy-python")
    DUKASCOPY_OK = False

# Mapping for easy use
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
    """Fetch forex data from Dukascopy"""
    if not DUKASCOPY_OK:
        return None
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    print(f"📡 Fetching {asset} {timeframe} data for last {days} days...")
    print(f"   From: {start.strftime('%Y-%m-%d')} To: {end.strftime('%Y-%m-%d')}")
    
    try:
        df = fetch(
            instrument=INSTRUMENT_MAP[asset],
            interval=INTERVAL_MAP[timeframe],
            offer_side=OFFER_SIDE_BID,
            start=start,
            end=end,
        )
        
        # Dukascopy returns DataFrame with datetime index
        print(f"   Raw data shape: {df.shape}")
        print(f"   Index type: {type(df.index)}")
        
        # Make sure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Adjust for Dukascopy's GMT+3 timezone
        df.index = df.index - timedelta(hours=3)
        
        # Add timestamp as a column (for compatibility with your analysis script)
        df['Timestamp'] = df.index
        
        # Reset index to make it a column (optional)
        # df = df.reset_index()  # Uncomment if you want index as column
        
        print(f"✅ Success! Retrieved {len(df)} candles")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Forex Data from Dukascopy',
        epilog='Examples:\n'
               '  python forex_fetcher.py -a GBP_USD -t 1h -d 30\n'
               '  python forex_fetcher.py -a EUR_USD -t 1d -d 365 -o eur_usd_yearly.csv'
    )
    
    parser.add_argument('-a', '--asset', default='EUR_USD',
                        choices=INSTRUMENT_MAP.keys(),
                        help='Forex pair (default: EUR_USD)')
    
    parser.add_argument('-t', '--timeframe', default='1h',
                        choices=INTERVAL_MAP.keys(),
                        help='Timeframe (default: 1h)')
    
    parser.add_argument('-d', '--days', type=int, default=30,
                        help='Number of days to fetch (default: 30)')
    
    parser.add_argument('-o', '--output', default=None,
                        help='Output CSV filename (default: auto-generated)')
    
    parser.add_argument('--no-save', action='store_true',
                        help='Don\'t save to file, just return data')
    
    args = parser.parse_args()
    
    # Generate output filename if not provided
    if not args.output and not args.no_save:
        args.output = f"{args.asset}_{args.timeframe}_{args.days}d.csv"
    
    # Fetch the data
    df = fetch_forex_data(args.asset, args.timeframe, args.days)
    
    if df is None:
        print("\n❌ Failed to fetch data. Check your internet connection and try again.")
        return 1
    
    # Display summary
    print(f"\n📊 Data Summary:")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    
    # Show date range (using index since it's the timestamp)
    print(f"   Date range: {df.index.min()} to {df.index.max()}")
    
    print(f"\n📈 First 5 rows:")
    print(df.head())
    
    print(f"\n📉 Last 5 rows:")
    print(df.tail())
    
    # Save to file
    if not args.no_save:
        # Save with index (timestamp) as first column
        df.to_csv(args.output)
        print(f"\n💾 Saved to: {args.output}")
        print(f"   File contains {len(df)} rows with columns: {', '.join(df.columns)}")
    
    return 0

if __name__ == '__main__':
    exit(main())#!/usr/bin/env python3
"""
Simple Forex Data Fetcher from Dukascopy
No complex dependencies, just works!
"""

import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

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
except ImportError as e:
    print(f"❌ Error importing dukascopy_python: {e}")
    print("   Install with: pip install dukascopy-python")
    DUKASCOPY_OK = False

# Mapping for easy use
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
    """Fetch forex data from Dukascopy"""
    if not DUKASCOPY_OK:
        return None
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    print(f"📡 Fetching {asset} {timeframe} data for last {days} days...")
    print(f"   From: {start.strftime('%Y-%m-%d')} To: {end.strftime('%Y-%m-%d')}")
    
    try:
        df = fetch(
            instrument=INSTRUMENT_MAP[asset],
            interval=INTERVAL_MAP[timeframe],
            offer_side=OFFER_SIDE_BID,
            start=start,
            end=end,
        )
        
        # Fix: Ensure we have a proper datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            print("   Converting index to DatetimeIndex...")
            df.index = pd.to_datetime(df.index)
        
        # Adjust for Dukascopy's GMT+3 timezone
        df.index = df.index - timedelta(hours=3)
        
        # Reset index to make Timestamp a column
        df = df.reset_index()
        df.rename(columns={'index': 'Timestamp'}, inplace=True)
        
        print(f"✅ Success! Retrieved {len(df)} candles")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Forex Data from Dukascopy',
        epilog='Examples:\n'
               '  python forex_fetcher.py -a GBP_USD -t 1h -d 30\n'
               '  python forex_fetcher.py -a EUR_USD -t 1d -d 365 -o eur_usd_yearly.csv'
    )
    
    parser.add_argument('-a', '--asset', default='EUR_USD',
                        choices=INSTRUMENT_MAP.keys(),
                        help='Forex pair (default: EUR_USD)')
    
    parser.add_argument('-t', '--timeframe', default='1h',
                        choices=INTERVAL_MAP.keys(),
                        help='Timeframe (default: 1h)')
    
    parser.add_argument('-d', '--days', type=int, default=30,
                        help='Number of days to fetch (default: 30)')
    
    parser.add_argument('-o', '--output', default=None,
                        help='Output CSV filename (default: auto-generated)')
    
    parser.add_argument('--no-save', action='store_true',
                        help='Don\'t save to file, just return data')
    
    args = parser.parse_args()
    
    # Generate output filename if not provided
    if not args.output and not args.no_save:
        args.output = f"{args.asset}_{args.timeframe}_{args.days}d.csv"
    
    # Fetch the data
    df = fetch_forex_data(args.asset, args.timeframe, args.days)
    
    if df is None:
        print("\n❌ Failed to fetch data. Check your internet connection and try again.")
        return 1
    
    # Display summary
    print(f"\n📊 Data Summary:")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print(f"\n📈 First 5 rows:")
    print(df.head())
    print(f"\n📉 Last 5 rows:")
    print(df.tail())
    
    # Save to file
    if not args.no_save:
        df.to_csv(args.output, index=False)
        print(f"\n💾 Saved to: {args.output}")
    
    return 0

if __name__ == '__main__':
    exit(main())
