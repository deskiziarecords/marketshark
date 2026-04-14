#!/usr/bin/env python3
"""
MarketShark Backend Engine
Flask REST API for token stream, vector similarity, decision logic, and reward tracking.
"""
import os
import sys
import time
import threading
import webbrowser
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

#  Fix import paths for src/ directory (works on Windows & Linux)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "src")
sys.path.insert(0, SRC_DIR)

#  Import custom modules
try:
    from vector_db import query_similar, get_collection
    from reward_tracker import log_trade, get_recent_performance, init_db as init_reward_db
except ImportError as e:
    print(f" Import Error: {e}")
    print(" Ensure 'src/vector_db.py' and 'src/reward_tracker.py' exist in the src/ folder.")
    sys.exit(1)

#  Flask App Setup
app = Flask(__name__, static_folder=CURRENT_DIR, static_url_path='')

#  Configuration
CONFIG = {
    "confidence_threshold": 0.75,
    "sl_pips": 8,
    "tp_pips": 16,
    "risk_per_trade": 0.005,
    "csv_path": os.path.join(CURRENT_DIR, "data", "eurusd_1min_tokenized.csv"),
    "host": "127.0.0.1",
    "port": 5000
}

#  Initialize databases on startup
init_reward_db()
print(" Reward DB initialized.")

#  Routes
@app.route("/")
def index():
    return send_from_directory(CURRENT_DIR, "MarketShark.html")

@app.route("/health")
def health():
    try:
        col = get_collection()
        count = col.count()
        return jsonify({"status": "ok", "chroma_patterns": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/stream")
def stream():
    try:
        if not os.path.exists(CONFIG["csv_path"]):
            return jsonify({"error": "Tokenized CSV not found"}), 404
        df = pd.read_csv(CONFIG["csv_path"], parse_dates=["timestamp"])
        return df.tail(200).to_json(orient="records", date_format="iso")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/similar", methods=["POST"])
def similar():
    try:
        data = request.json
        token_window = data.get("tokens", "")
        if not token_window:
            return jsonify({"error": "Missing 'tokens' field"}), 400
        results = query_similar(token_window, n_results=5)
        return jsonify({"matches": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/decision", methods=["POST"])
def decision():
    try:
        data = request.json
        token_window = data.get("tokens", "")
        price = data.get("price", 1.0)

        # 1️ Vector similarity search
        matches = query_similar(token_window, n_results=5, min_win_rate=0.5)
        base_conf = 0.5
        best_match = None

        if matches:
            best_match = matches[0]
            base_conf = best_match["win_rate"] * 0.7 + best_match["similarity"] * 0.3

        # 2️ Adaptive threshold based on recent performance
        recent_perf = get_recent_performance(hours=24)
        threshold = CONFIG["confidence_threshold"]
        if recent_perf["total"] > 5:
            avg_r = recent_perf["avg_reward"]
            if avg_r < -0.5: threshold += 0.10
            elif avg_r > 0.8: threshold -= 0.05
            elif avg_r < 0.0: threshold += 0.07
        threshold = max(0.65, min(0.90, threshold))

        # 3️ Decision logic
        action = "WAIT"
        source = "local_vector"
        if base_conf >= threshold and best_match:
            action = "BUY" if best_match.get("avg_rr", 0) > 0 else "SELL"
        else:
            source = "below_threshold" # LLM fallback placeholder

        return jsonify({
            "action": action,
            "confidence": round(base_conf, 3),
            "threshold": round(threshold, 3),
            "source": source,
            "pattern": best_match,
            "risk": {
                "sl_pips": CONFIG["sl_pips"],
                "tp_pips": CONFIG["tp_pips"],
                "risk_per_trade": CONFIG["risk_per_trade"]
            },
            "recent_performance": recent_perf
        })
    except Exception as e:
        return jsonify({"error": str(e), "action": "WAIT", "confidence": 0.0}), 500

@app.route("/log_trade", methods=["POST"])
def log_trade_endpoint():
    try:
        trade_data = request.json
        required = ["pattern", "tokens", "direction", "entry_price", "exit_price", "pips", "pnl_pct", "confidence"]
        for field in required:
            if field not in trade_data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        reward = log_trade(trade_data)
        return jsonify({"reward_score": reward, "status": "logged"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reward_stats")
def reward_stats():
    try:
        return jsonify(get_recent_performance(hours=24))
    except Exception as e:
        return jsonify({"win_rate": 0.0, "avg_reward": 0.0, "total": 0, "pnl_pct": 0.0, "error": str(e)}), 200

#  Auto-launch browser on startup
def open_browser():
    time.sleep(2.5)
    webbrowser.open(f"http://{CONFIG['host']}:{CONFIG['port']}")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print(" MarketShark Engine Starting...")
    print(f" UI: http://{CONFIG['host']}:{CONFIG['port']}")
    print(f" CSV: {CONFIG['csv_path']}")
    print(f" DB: src/trade_rewards.db + chroma_db/")
    app.run(host=CONFIG["host"], port=CONFIG["port"], debug=False)
