#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
import dukascopy_python
from dukascopy_python.instruments import *

# Map instruments
INSTRUMENTS = {
    'EUR_USD': INSTRUMENT_FX_MAJORS_EUR_USD,
    'GBP_USD': INSTRUMENT_FX_MAJORS_GBP_USD,
    'USD_JPY': INSTRUMENT_FX_MAJORS_USD_JPY,
    'USD_CHF': INSTRUMENT_FX_MAJORS_USD_CHF,
    'AUD_USD': INSTRUMENT_FX_MAJORS_AUD_USD,
    'USD_CAD': INSTRUMENT_FX_MAJORS_USD_CAD,
    'NZD_USD': INSTRUMENT_FX_MAJORS_NZD_USD,
}

TIMEFRAMES = {
    '1m': dukascopy_python.INTERVAL_MIN_1,
    '5m': dukascopy_python.INTERVAL_MIN_5,
    '15m': dukascopy_python.INTERVAL_MIN_15,
    '30m': dukascopy_python.INTERVAL_MIN_30,
    '1h': dukascopy_python.INTERVAL_HOUR_1,
    '4h': dukascopy_python.INTERVAL_HOUR_4,
    '1d': dukascopy_python.INTERVAL_DAY_1,
}

def main():
    parser = argparse.ArgumentParser(description='Fetch Forex data from Dukascopy')
    parser.add_argument('-a', '--asset', default='EUR_USD', 
                        choices=INSTRUMENTS.keys(),
                        help='Forex pair (default: EUR_USD)')
    parser.add_argument('-t', '--timeframe', default='1m',
                        choices=TIMEFRAMES.keys(),
                        help='Timeframe (default: 1m)')
    parser.add_argument('-d', '--days', type=int, default=365,
                        help='Number of days to fetch (default: 365)')
    parser.add_argument('-o', '--output', help='Output filename (optional)')
    
    args = parser.parse_args()
    
    # Calculate dates
    end = datetime.now()
    start = end - timedelta(days=args.days)
    
    # Fetch data
    print(f"Fetching {args.asset} {args.timeframe} data for last {args.days} days...")
    df = dukascopy_python.fetch(
        instrument=INSTRUMENTS[args.asset],
        interval=TIMEFRAMES[args.timeframe],
        offer_side=dukascopy_python.OFFER_SIDE_BID,
        start=start,
        end=end,
    )
    
    # Adjust timestamp
    df.index = df.index - timedelta(hours=3)
    
    # Save to file
    if args.output:
        filename = args.output
    else:
        filename = f"{args.asset}_{args.timeframe}_{args.days}days.csv"
    
    df.to_csv(filename)
    print(f"✓ Saved to {filename}")
    print(f"✓ Shape: {df.shape}")
    print(df.head())

if __name__ == "__main__":
    main()
