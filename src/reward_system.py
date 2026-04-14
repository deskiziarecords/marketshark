#!/usr/bin/env python3
"""
reward_system.py
Tracks trade outcomes, calculates reward scores, adapts decision thresholds,
and syncs performance metrics back to ChromaDB.
"""
import sqlite3
import os
import numpy as np
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_rewards.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pattern TEXT,
                tokens TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                pips REAL,
                pnl_pct REAL,
                confidence REAL,
                context_multiplier REAL,
                reward_score REAL,
                hold_minutes REAL,
                status TEXT DEFAULT 'CLOSED'
            );
            CREATE TABLE IF NOT EXISTS pattern_stats (
                pattern TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                avg_pips REAL DEFAULT 0.0,
                avg_rr REAL DEFAULT 0.0,
                win_streak INTEGER DEFAULT 0,
                loss_streak INTEGER DEFAULT 0,
                recent_reward REAL DEFAULT 0.0,
                last_updated TEXT
            );
        """)

def calculate_reward(pnl_pct, confidence, hold_minutes):
    is_win = pnl_pct > 0
    base = (pnl_pct * 100) * (confidence if is_win else confidence * 0.5)
    time_factor = max(0.5, min(1.5, 60 / max(hold_minutes, 5)))
    streak_bonus = 0.2 if (is_win and confidence > 0.8) else -0.3 if (not is_win and confidence > 0.7) else 0
    return round((base + streak_bonus) * time_factor, 2)

def log_trade(trade_data):
    init_db()
    pnl_pct = trade_data.get("pnl_pct", 0.0)
    conf = trade_data.get("confidence", 0.5)
    hold_min = trade_data.get("hold_minutes", 30)
    reward = calculate_reward(pnl_pct, conf, hold_min)
    
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (timestamp, pattern, tokens, direction, entry_price, exit_price,
                                pips, pnl_pct, confidence, context_multiplier, reward_score, hold_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(), trade_data.get("pattern", ""),
            trade_data.get("tokens", ""), trade_data.get("direction", "UNKNOWN"),
            trade_data.get("entry_price"), trade_data.get("exit_price"),
            trade_data.get("pips"), pnl_pct, conf,
            trade_data.get("context_multiplier", 1.0), reward, hold_min
        ))
        
        pat = trade_data.get("pattern")
        if pat:
            row = cur.execute("SELECT * FROM pattern_stats WHERE pattern=?", (pat,)).fetchone()
            if row:
                total, wins, losses, avg_p, avg_rr, ws, ls, rr, _ = row[1:]
                total += 1
                if pnl_pct > 0:
                    wins += 1; ws += 1; ls = 0
                else:
                    losses += 1; ls += 1; ws = 0
                avg_p = (avg_p * (total-1) + trade_data.get("pips", 0)) / total
                avg_rr = avg_p / 8.0
                rr = 0.3 * reward + 0.7 * rr  # EMA
                cur.execute("""
                    UPDATE pattern_stats SET total_trades=?, wins=?, losses=?, avg_pips=?,
                                             avg_rr=?, win_streak=?, loss_streak=?, recent_reward=?, last_updated=?
                    WHERE pattern=?
                """, (total, wins, losses, round(avg_p,2), round(avg_rr,2), ws, ls, round(rr,2),
                      datetime.utcnow().isoformat(), pat))
            else:
                cur.execute("""
                    INSERT INTO pattern_stats (pattern, total_trades, wins, losses, avg_pips, avg_rr,
                                               win_streak, loss_streak, recent_reward, last_updated)
                    VALUES (?, 1, 1, 0, ?, ?, 1, 0, ?, ?)
                """, (pat, round(trade_data.get("pips",0),2), round(trade_data.get("pips",0)/8.0,2),
                      round(reward,2), datetime.utcnow().isoformat()))
        conn.commit()
    return reward

def get_adaptive_threshold(pattern=None, base=0.75, lookback_hours=24):
    init_db()
    cutoff = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        df = __import__('pandas').read_sql("""
            SELECT pnl_pct, reward_score, confidence FROM trades WHERE timestamp > ?
        """, conn, params=(cutoff,))
        
    if df.empty or len(df) < 5:
        return base
        
    avg_r = df["reward_score"].mean()
    adj = 0.0
    if avg_r < -0.5: adj += 0.10
    elif avg_r > 0.8: adj -= 0.05
    elif avg_r < 0.0: adj += 0.07
        
    if pattern:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT win_streak, loss_streak, recent_reward FROM pattern_stats WHERE pattern=?", (pattern,)).fetchone()
            if row:
                ws, ls, rr = row
                if ws >= 3 and rr > 0: adj -= 0.07
                elif ls >= 2: adj += 0.10
                
    return round(max(0.65, min(0.85, base + adj)), 2)

def get_recent_performance(hours=24):
    init_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        df = __import__('pandas').read_sql("""
            SELECT pnl_pct, reward_score FROM trades WHERE timestamp > ?
        """, conn, params=(cutoff,))
    if df.empty:
        return {"win_rate": 0.0, "avg_reward": 0.0, "total": 0, "pnl_pct": 0.0}
    return {
        "win_rate": round((df["pnl_pct"] > 0).mean(), 3),
        "avg_reward": round(df["reward_score"].mean(), 2),
        "total": len(df),
        "pnl_pct": round(df["pnl_pct"].sum(), 4)
    }

def sync_to_chroma():
    init_db()
    try:
        from src.vector_db import get_collection
        collection = get_collection()
        with sqlite3.connect(DB_PATH) as conn:
            stats = conn.execute("SELECT pattern, avg_pips, avg_rr, recent_reward, win_streak, loss_streak FROM pattern_stats").fetchall()
        for pat, avg_p, avg_rr, rr_score, ws, ls in stats:
            try:
                collection.update(
                    ids=[pat],
                    metadatas=[{"avg_pips": avg_p, "avg_rr": avg_rr, "recent_reward": rr_score,
                                "win_streak": ws, "loss_streak": ls, "last_sync": datetime.utcnow().isoformat()}]
                )
            except Exception:
                pass  # Skip if pattern not yet in ChromaDB
    except Exception:
        pass  # Graceful fallback if DB not ready
