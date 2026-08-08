"""
Optional real-LLM client, used ONLY when MOCK_LLM=0 (ungraded extension).

Defaults to Groq's free-tier API (console.groq.com) via its OpenAI-compatible
endpoint. Set GROQ_API_KEY (or point BASE_URL/MODEL at any other free-tier
OpenAI-compatible API) as environment variables / a Space secret -- never
hardcode a key in source.

Nothing in this file is imported or executed on the default (MOCK_LLM=1)
graded path.
"""
import os
import urllib.request
import json

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")


def call_llm(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MOCK_LLM=0 was set but no GROQ_API_KEY / LLM_API_KEY is configured. "
            "This optional path requires a free-tier API key; the graded default "
            "path (MOCK_LLM=1) does not need one."
        )

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]
