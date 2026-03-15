"""Быстрый тест: 1 запрос к LLM, смотрим что возвращает."""

from llm_client import LLMClient
import json

client = LLMClient()

messages = [
    {"role": "system", "content": "You generate realistic hotel reviews. Return ONLY a JSON array."},
    {"role": "user", "content": """Generate 3 hotel reviews for "The Plaza Hotel" in New York, US (5-star).

Each review is a JSON object:
- "author": first name
- "country": 2-letter ISO code
- "vacation_type": one of ["family","solo","couple","business","friends"]
- "rating": float 1.0-10.0
- "good_part": 2-3 sentences
- "bad_part": string or null
- "common_text": string or null

Return ONLY a JSON array."""}
]

print("📡 Отправляю запрос к LLM...")
print()

# Сырой ответ
raw = client.request(messages, max_tokens=2048, temperature=0.9)
print("=== RAW RESPONSE ===")
print(raw)
print()

# Парсинг в JSON
parsed = client.request_json(messages, max_tokens=2048, temperature=0.9)
print("=== PARSED JSON ===")
print(type(parsed))
print(json.dumps(parsed, indent=2, ensure_ascii=False) if parsed else "None — парсинг не удался")