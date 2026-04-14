#!/usr/bin/env python3
"""
backend.py
Flask API with: ChromaDB vector search + Ollama fallback + risk-managed execution
"""
from flask import Flask, jsonify, request
import pandas as pd
import os
from vector_db import query_similar, get_pattern_stats
from llm_fallback import get_decision_fallback
from embeddings import embed_sequence

app = Flask(__name__)

CONFIG = {
    "confidence_threshold": 0.75,
    "ollama_model": "llama3.2:1b",
    "risk_per_trade": 0.005,
    "default_sl_pips": 8,
    "default_tp_pips": 16
}

@app.route('/health')
def health():
    return jsonify({"status": "ok", "db": get_pattern_stats()})

@app.route('/stream')
def stream():
    """Serve latest tokenized rows"""
    df = pd.read_csv("eurusd_1min_tokenized.csv", parse_dates=["timestamp"]).tail(200)
    return df.to_json(orient="records", date_format="iso")

@app.route('/similar', methods=['POST'])
def similar():
    """Vector similarity search"""
    data = request.json
    token_window = data.get("tokens", "")
    results = query_similar(token_window, n_results=5)
    return jsonify({"matches": results})

@app.route('/decision', methods=['POST'])
def decision():
    """Full decision pipeline: local → Ollama → Cloud"""
    data = request.json
    token_window = data.get("tokens", "")
    price = data.get("price", 1.0)
    
    # Step 1: Local vector match
    local_matches = query_similar(token_window, n_results=5, min_win_rate=0.5)
    
    if local_matches:
        best = local_matches[0]
        confidence = best["win_rate"] * 0.7 + best["similarity"] * 0.3
        direction = "BUY" if best["avg_rr"] > 0 else "SELL"
        
        if confidence >= CONFIG["confidence_threshold"]:
            return jsonify({
                "action": direction,
                "confidence": round(confidence, 3),
                "source": "local_vector",
                "pattern": best,
                "risk": {
                    "position_size": CONFIG["default_sl_pips"],  # Simplified
                    "stop_loss": CONFIG["default_sl_pips"],
                    "take_profit": CONFIG["default_tp_pips"]
                }
            })
    
    # Step 2: LLM fallback
    llm_result = get_decision_fallback(token_window, price, local_matches, CONFIG)
    
    return jsonify({
        "action": llm_result["decision"],
        "confidence": round(llm_result["confidence"], 3),
        "source": llm_result["source"],
        "reasoning": llm_result.get("reasoning", ""),
        "local_matches": local_matches[:3],  # Include top matches for UI
        "risk": {
            "position_size": CONFIG["default_sl_pips"],
            "stop_loss": CONFIG["default_sl_pips"],
            "take_profit": CONFIG["default_tp_pips"]
        }
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
