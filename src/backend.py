import os, sys, time, threading, webbrowser
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from vector_db import query_similar
from llm_fallback import get_decision_fallback

app = Flask(__name__)
CONFIG = {"confidence_threshold": 0.75, "ollama_model": "llama3.2:1b", "sl_pips": 8, "tp_pips": 16}

@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), '..', "MarketShark.html")

@app.route("/health")
def health(): return jsonify({"status": "ok"})

@app.route("/stream")
def stream():
    csv = os.path.join(os.path.dirname(__file__), '..', "data", "eurusd_1min_tokenized.csv")
    if not os.path.exists(csv): return jsonify({"error": "CSV missing"}), 404
    return pd.read_csv(csv, parse_dates=["timestamp"]).tail(200).to_json(orient="records", date_format="iso")

@app.route("/similar", methods=["POST"])
def similar():
    return jsonify({"matches": query_similar(request.json.get("tokens", ""), n_results=5)})

@app.route("/decision", methods=["POST"])
def decision():
    tw = request.json.get("tokens", "")
    price = request.json.get("price", 1.0)
    matches = query_similar(tw, n_results=5, min_win_rate=0.5)
    if matches:
        best = matches[0]
        conf = best["win_rate"] * 0.7 + best["similarity"] * 0.3
        if conf >= CONFIG["confidence_threshold"]:
            return jsonify({"action": "BUY" if best["avg_rr"]>0 else "SELL", "confidence": round(conf,3), "source": "local_vector", "pattern": best, "risk": CONFIG})
    llm = get_decision_fallback(tw, price, matches, CONFIG)
    return jsonify({"action": llm["decision"], "confidence": round(llm["confidence"],3), "source": llm["source"], "reasoning": llm.get("reasoning",""), "local_matches": matches[:3], "risk": CONFIG})

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print("🚀 MarketShark Engine running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
