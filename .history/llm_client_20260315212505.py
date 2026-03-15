"""Асинхронный клиент к LLM proxy с retry."""

import asyncio
import json as json_lib
import httpx
from typing import Optional, Union
from config import LLM_PROXY_URL, LLM_API_KEY, LLM_MODEL, MAX_RETRIES


class LLMClient:
    """Синхронный клиент (для тестов)."""

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
            except Exception:
                pass
        return None

    def request_json(self, messages, max_tokens=4096, temperature=0.9):
        # type: (list, int, float) -> Optional[Union[dict, list]]
        raw = self.request(messages, max_tokens=max_tokens, temperature=temperature)
        return _parse_json(raw)


class AsyncLLMClient:
    """Асинхронный клиент с retry и обработкой ошибок."""

    def __init__(self, max_concurrent=5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._client = None

    async def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=LLM_PROXY_URL,
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                verify=False,
                timeout=120.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(self, messages, max_tokens=4096, temperature=0.9):
        # type: (list, int, float) -> Optional[str]
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
            "temperature": temperature,
            "top_p": 0.95,
        }

        async with self.semaphore:
            client = await self._get_client()

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await client.post("/chat/completions", json=payload)
                    response.raise_for_status()
                    data = response.json()

                    if data and "choices" in data:
                        content = data["choices"][0]["message"]["content"]
                        if content and len(content.strip()) > 10:
                            return content

                    print(f"      ⚠️  Пустой ответ (попытка {attempt}/{MAX_RETRIES})")

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status == 429:
                        wait = int(e.response.headers.get("Retry-After", 5 * attempt))
                        print(f"      ⏳ 429 Rate limit, жду {wait}с (попытка {attempt}/{MAX_RETRIES})")
                        await asyncio.sleep(wait)
                    elif status in (500, 502, 503):
                        wait = 3 * attempt
                        print(f"      ⚠️  {status}, жду {wait}с (попытка {attempt}/{MAX_RETRIES})")
                        await asyncio.sleep(wait)
                    else:
                        print(f"      ❌ HTTP {status} (попытка {attempt}/{MAX_RETRIES})")
                        await asyncio.sleep(2)

                except httpx.ReadTimeout:
                    wait = 5 * attempt
                    print(f"      ⏳ Timeout, жду {wait}с (попытка {attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)

                except httpx.ConnectError:
                    wait = 5 * attempt
                    print(f"      ❌ ConnectError, жду {wait}с (попытка {attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)

                except Exception as e:
                    print(f"      ❌ {type(e).__name__}: {e} (попытка {attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(2)

        return None

    async def request_json(self, messages, max_tokens=4096, temperature=0.9):
        # type: (list, int, float) -> Optional[Union[dict, list]]
        raw = await self.request(messages, max_tokens=max_tokens, temperature=temperature)
        return _parse_json(raw)


def _parse_json(raw):
    # type: (Optional[str]) -> Optional[Union[dict, list]]
    """Парсит JSON из сырого ответа LLM."""
    if not raw:
        return None

    text = raw.strip()

    # Убираем markdown-обёртку
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