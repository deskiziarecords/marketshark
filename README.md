# marketshark
[https://github.com/deskiziarecords/marketshark/blob/main/market-shark.jpg?raw=true]
m shark
``` text
MarketShark_EURUSD/
├── 📂 data/
│   └── eurusd_1min_tokenized.csv   # Your 7-year tokenized input
├── 📂 src/
│   ├── embeddings.py               # Token → 384D vector (sentence-transformers)
│   ├── vector_db.py                # ChromaDB wrapper (similarity search + metadata)
│   ├── llm_fallback.py             # Ollama → Cloud fallback chain
│   └── backend.py                  # Flask server + decision engine + risk routing
├── MarketShark.html                # Final Wireshark-style UI
├── mine_patterns.py                # One-time setup script (populates ChromaDB)
├── requirements.txt                # Python dependencies
└── build.bat                       # One-click PyInstaller packaging
```
