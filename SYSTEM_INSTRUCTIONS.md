# MarketShark System Instructions

This document provides a set of guidelines and instructions for operating, maintaining, and extending the MarketShark system.

## 1. Operating Principles

- **Local-First**: Prioritize local processing (ChromaDB, local embeddings, Ollama) over cloud dependencies to ensure low latency and data privacy.
- **Token-Native**: Always treat market data as a sequence of discrete tokens (A-Z). Avoid mixing raw OHLCV values into the core pattern matching logic.
- **Micro-Structural Integrity**: Use the forensic suite (`carver`, `scanner`, `extractor`) to validate market context before committing to a decision based solely on similarity.

## 2. Maintenance Procedures

### Updating the Pattern Database
To update the pattern database with new historical data:
1.  Place the new tokenized CSV in the `data/` directory.
2.  Run `python mine_patterns.py path/to/your/file.csv`.
3.  Verify the updated pattern count via the `/health` endpoint.

### Performance Monitoring
- Check `src/trade_rewards.db` regularly to assess the performance of different patterns.
- Monitor `backend.log` (if enabled) for any LLM fallback failures or database latency issues.

## 3. Extension Guidelines

### Adding New Forensic Features
- Implement new feature detectors as static methods in `src/bulk_extractor.py`.
- Register them in the `MarketFeatureExtractor.__init__` features dictionary.
- Ensure they return a Boolean Pandas Series.

### Supporting New Assets
1.  Create a new collection in ChromaDB (update `COLLECTION_NAME` in `src/vector_db.py`).
2.  Configure the appropriate `csv_path` and `port` in `backend.py` (consider using environment variables for asset-specific instances).
3.  Re-run the pattern mining script for the specific asset data.

## 4. Troubleshooting

- **ChromaDB Errors**: Ensure the `chroma_db/` directory is writable and that no other process is locking the persistent store.
- **JSON Serialization Errors**: When adding new API endpoints, always convert Pandas Series/DataFrames to dictionaries using `.to_dict()` before passing them to `jsonify`.
- **Inference Latency**: If LLM fallback is too slow, ensure Ollama is running on a GPU-enabled instance or switch to a smaller model (e.g., `phi3:mini` or `llama3.2:1b`).
