#!/usr/bin/env python3
"""
llm_fallback.py
Local-first LLM fallback: Ollama/LM Studio → Cloud API only if needed.
"""
import requests
import json
import os
from typing import Optional

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "")  # Optional: your frontier model endpoint
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")

def query_ollama(prompt: str, model: str = "llama3.2:1b", timeout: int = 30) -> Optional[dict]:
    """
    Query local Ollama/LM Studio instance.
    Returns parsed JSON response or None if failed.
    """
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Request JSON output
            "options": {
                "temperature": 0.1,
                "num_predict": 256
            }
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        
        # Parse LLM response
        content = result.get("response", "")
        if content:
            # Extract JSON from markdown/code blocks if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            decision = json.loads(content)
            return {
                "source": "ollama",
                "model": model,
                "decision": decision.get("action", "WAIT"),
                "confidence": float(decision.get("confidence", 0.5)),
                "reasoning": decision.get("reasoning", ""),
                "raw": content
            }
    except Exception as e:
        print(f"[Ollama Error] {e}")
    return None

def query_cloud_api(prompt: str, token_window: str, price: float) -> Optional[dict]:
    """
    Fallback to cloud frontier model (only if Ollama fails or is disabled).
    """
    if not CLOUD_API_URL:
        return None
        
    try:
        payload = {
            "model": "gpt-4o-mini",  # or your preferred model
            "messages": [
                {"role": "system", "content": "You are a forex trading assistant. Respond in JSON with keys: action, confidence, reasoning."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200,
            "response_format": {"type": "json_object"}
        }
        headers = {
            "Authorization": f"Bearer {CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post(CLOUD_API_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        decision = json.loads(content)
        return {
            "source": "cloud",
            "decision": decision.get("action", "WAIT"),
            "confidence": float(decision.get("confidence", 0.5)),
            "reasoning": decision.get("reasoning", "")
        }
    except Exception as e:
        print(f"[Cloud API Error] {e}")
    return None

def get_decision_fallback(token_window: str, price: float, local_matches: list, config: dict) -> dict:
    """
    Full fallback chain:
    1. Local vector match (already done)
    2. Local LLM (Ollama) if confidence low
    3. Cloud API only if Ollama fails
    """
    # Build prompt for LLM
    pattern_summary = "\n".join([
        f"- {m['pattern']}: WR={m['win_rate']:.2f}, RR={m['avg_rr']:.2f}, sim={m['similarity']:.3f}"
        for m in local_matches[:3]
    ]) if local_matches else "No similar patterns found."
    
    prompt = f"""
    EUR/USD 1-minute trading decision.
    Current price: {price:.5f}
    Recent token sequence (30 chars): {token_window}
    
    Similar historical patterns:
    {pattern_summary}
    
    Respond in JSON format ONLY:
    {{
      "action": "BUY" or "SELL" or "WAIT",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }}
    """.strip()
    
    # Try Ollama first
    ollama_result = query_ollama(prompt, model=config.get("ollama_model", "llama3.2:1b"))
    if ollama_result and ollama_result["confidence"] >= 0.6:
        return ollama_result
    
    # Fallback to cloud
    cloud_result = query_cloud_api(prompt, token_window, price)
    if cloud_result:
        return cloud_result
    
    # Final fallback: wait
    return {
        "source": "fallback",
        "decision": "WAIT",
        "confidence": 0.3,
        "reasoning": "All models uncertain; awaiting clearer signal"
    }
