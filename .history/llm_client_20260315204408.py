"""Асинхронный + синхронный клиент к LLM proxy."""

import time
import json as json_lib
import httpx
from typing import Optional, Union
from config import LLM_PROXY_URL, LLM_API_KEY, LLM_MODEL, MAX_RETRIES


class LLMClient:
    def __init__(self):
        self.http_client = httpx.Client(
            base_url=LLM_PROXY_URL,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=120.0,
        )

    def request(self, messages, max_tokens=4096, temperature=0.9, top_p=0.95):
        # type: (list, int, float, float) -> Optional[str]
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = self.http_client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                if data and "choices" in data:
                    return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 10))
                    time.sleep(retry_after)
                elif status in (500, 502, 503):
                    time.sleep(3)
                else:
                    break
            except httpx.ReadTimeout:
                time.sleep(5)
            except Exception:
                break
        return None

    def request_json(self, messages, max_tokens=4096, temperature=0.9):
        # type: (list, int, float) -> Optional[Union[dict, list]]
        raw = self.request(messages, max_tokens=max_tokens, temperature=temperature)
        if not raw:
            return None

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[start:end])

        try:
            return json_lib.loads(text)
        except json_lib.JSONDecodeError:
            for sc, ec in [("[", "]"), ("{", "}")]:
                s = text.find(sc)
                e = text.rfind(ec)
                if s != -1 and e > s:
                    try:
                        return json_lib.loads(text[s:e + 1])
                    except json_lib.JSONDecodeError:
                        continue
            return None