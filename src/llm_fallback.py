import requests
import json
import os
from typing import Optional

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")

def _parse_json(content: str) -> Optional[dict]:
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except:
        return None

def query_ollama(prompt: str, model: str = "llama3.2:1b", timeout: int = 30) -> Optional[dict]:
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        res = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        res.raise_for_status()
        data = _parse_json(res.json().get("response", ""))
        if data and "action" in data:
            return {
                "source": "ollama",
                "decision": data.get("action", "WAIT"),
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning": data.get("reasoning", "")
            }
    except Exception as e:
        print(f"[Ollama Error] {e}")
    return None

def query_cloud(prompt: str) -> Optional[dict]:
    if not CLOUD_API_URL or not CLOUD_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Forex assistant. JSON only: {action,confidence,reasoning}"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(CLOUD_API_URL, json=payload, headers=headers, timeout=20)
        res.raise_for_status()
        data = _parse_json(res.json()["choices"][0]["message"]["content"])
        if data and "action" in data:
            return {
                "source": "cloud",
                "decision": data.get("action", "WAIT"),
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning": data.get("reasoning", "")
            }
    except Exception as e:
        print(f"[Cloud Error] {e}")
    return None

def get_decision_fallback(token_window: str, price: float, local_matches: list, config: dict) -> dict:
    pat_sum = "\n".join([
        f"- {m['pattern']}: WR={m['win_rate']:.2f}, RR={m['avg_rr']:.2f}"
        for m in local_matches[:3]
    ]) if local_matches else "No patterns."
    
    prompt = f"""
EUR/USD 1-min trade.
Price: {price:.5f}
Seq: {token_window}
History:
{pat_sum}

JSON ONLY: {{"action": "BUY/SELL/WAIT", "confidence": 0.0-1.0, "reasoning": "..."}}
""".strip()

    res = query_ollama(prompt, config.get("ollama_model", "llama3.2:1b"))
    if res and res["confidence"] >= 0.6:
        return res
        
    res = query_cloud(prompt)
    if res:
        return res
        
    return {
        "source": "fallback",
        "decision": "WAIT",
        "confidence": 0.3,
        "reasoning": "Models uncertain"
    }
