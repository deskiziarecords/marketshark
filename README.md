# MarketShark | Token-Native Forex Pattern Recognition System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-orange)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

**A Wireshark-inspired market analyzer that converts price action into token sequences, 
stores patterns in a local vector database, and uses LLM fallback for low-confidence decisions.**

</div>

---

## 🦈 Overview

MarketShark is a **local-first, asset-isolated trading intelligence system** that treats market data as a language. Instead of analyzing floating-point OHLCV values directly, the system:

1. **Tokenizes** candlestick patterns into discrete letters (A-Z).
2. **Embeds** token sequences into 384-dimensional vectors using `all-MiniLM-L6-v2`.
3. **Stores** historical patterns in **ChromaDB** with win-rate metadata.
4. **Matches** real-time sequences against historical patterns using cosine similarity.
5. **Analyzes** market micro-structure via a suite of forensic tools (Carver, Scanner, Extractor).
6. **Decides** via local confidence thresholds or LLM fallback (Ollama → Cloud API).

---

## 📂 Project Structure

```text
marketshark/
├── 📂 data/                 # Historical data & tokenized outputs
├── 📂 src/                  # Core engine modules
│   ├── embeddings.py        # Token → 384D vector (sentence-transformers)
│   ├── vector_db.py         # ChromaDB wrapper (similarity search + metadata)
│   ├── carver.py            # Market structure zone extraction
│   ├── bulk_extractor.py    # Parallel feature extraction
│   ├── reward_tracker.py    # SQLite-based trade & performance logging
│   └── backend.py           # Flask REST API + decision engine
├── 📂 tests/                # System verification & smoke tests
├── MarketShark.html         # Wireshark-style frontend UI
├── mine_patterns.py         # Pattern mining & indexing script
├── requirements.txt         # Python dependencies
└── SYSTEM_INSTRUCTIONS.md   # Guidelines for system operation
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Prepare the Database
Ensure you have a tokenized CSV in `data/eurusd_1min_tokenized.csv`, then run:
```bash
python mine_patterns.py
```

### 3. Start the Backend
```bash
python backend.py
```
The UI will automatically open in your browser at `http://127.0.0.1:5000`.

### 4. Run Tests
```bash
python tests/smoke_test.py
```

---

## 🛠 Features

- **Vector Similarity Search**: Powered by ChromaDB for sub-50ms pattern matching.
- **Forensic Suite**:
    - **Carver**: Extracts accumulation and distribution zones.
    - **Scanner**: Identifies specific market signatures.
    - **Extractor**: High-speed parallel extraction of micro-structural features.
- **Adaptive Decision Engine**: Adjusts confidence thresholds based on recent performance.
- **Hybrid LLM Fallback**: Seamless integration with local Ollama or Cloud APIs for complex scenarios.
- **Wireshark-Style UI**: Detailed inspection of the token stream and market "packets".

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.
