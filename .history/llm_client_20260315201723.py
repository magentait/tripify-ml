"""
Клиент для обращения к LLM proxy.
Адаптировано из твоего OpenAIRequest.
"""

import time
import json as json_lib
import httpx
from config import LLM_PROXY_URL, LLM_API_KEY, LLM_MODEL, MAX_RETRIES
from typing import Optional, Union


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

    def request(self, messages: list, max_tokens: int = 4096,
                temperature: float = 0.9, top_p: float = 0.95) -> Optional[str]:
        """
        Отправляет запрос к LLM proxy и возвращает текст ответа.

        Args:
            messages: список сообщений [{role, content}, ...]
            max_tokens: максимум токенов в ответе
            temperature: креативность (0.9 для живых отзывов)
            top_p: nucleus sampling

        Returns:
            str: текст ответа модели или None при ошибке
        """
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
                    content = data["choices"][0]["message"]["content"]
                    return content

                print(f"  ⚠️  Пустой ответ от модели (попытка {attempt + 1})")

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 10))
                    print(f"  ⏳ Rate limit (429), жду {retry_after}с...")
                    time.sleep(retry_after)
                elif status in (500, 502, 503):
                    print(f"  ⚠️  Ошибка {status}, жду 5с... (попытка {attempt + 1})")
                    time.sleep(5)
                else:
                    print(f"  ❌ HTTP {status}: {e}")
                    break

            except httpx.ReadTimeout:
                print(f"  ⏳ Timeout, жду 10с... (попытка {attempt + 1})")
                time.sleep(10)

            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                break

        return None

    def request_json(self, messages: list, max_tokens: int = 4096,
                     temperature: float = 0.9) -> Optional[Union[dict, list]]:
        """
        Отправляет запрос и парсит ответ как JSON.
        Обрабатывает случаи, когда модель оборачивает JSON в ```json ... ```
        """
        raw = self.request(messages, max_tokens=max_tokens, temperature=temperature)
        if not raw:
            return None

        # Убираем markdown-обёртку
        text = raw.strip()
        if text.startswith("```"):
            # ```json\n...\n```  или  ```\n...\n```
            lines = text.split("\n")
            # Убираем первую строку (```json) и последнюю (```)
            start = 1
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[start:end])

        # Иногда модель добавляет текст до/после JSON — ищем [ ] или { }
        try:
            return json_lib.loads(text)
        except json_lib.JSONDecodeError:
            # Пробуем найти JSON-массив или объект в тексте
            for start_char, end_char in [("[", "]"), ("{", "}")]:
                s = text.find(start_char)
                e = text.rfind(end_char)
                if s != -1 and e != -1 and e > s:
                    try:
                        return json_lib.loads(text[s:e + 1])
                    except json_lib.JSONDecodeError:
                        continue

            print(f"  ❌ Не удалось распарсить JSON. Начало ответа: {text[:200]}")
            return None