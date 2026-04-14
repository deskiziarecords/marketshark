# Basic fetch (1 year)
python fetch_dukascopy.py --symbol EURUSD --start 2024-01-01 --end 2024-12-31

# Fetch 7 years (resume-safe)
python fetch_dukascopy.py --symbol EURUSD --start 2019-04-09 --end 2026-04-13 --resume

# Custom output + verbose logging
python fetch_dukascopy.py --symbol GBPJPY --start 2025-01-01 --end 2025-01-07 --output gbpjpy_1min.csv --verbose
