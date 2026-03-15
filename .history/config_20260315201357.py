"""Конфигурация проекта."""

# ── LLM Proxy ──
LLM_PROXY_URL = "https://llm-proxy.t-tech.team"
LLM_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X2lkIjo0MTQsImV4cCI6NDkwMzA3NzA0NCwiaWF0IjoxNzQ5NDc3MDQ0LCJpZCI6MzYxLCJpc3MiOiJsbG0tcHJveHkifQ.egjIdutXlp7DkakVAQkrd7sszfCgtgZvy7OLDd9TU3A"
LLM_MODEL = "tgpt/qwen3-235b-a22b-instruct-2507"

# ── Генерация ──
TOTAL_HOTELS = 1000
COMMENTS_PER_HOTEL = 8
OUTPUT_FILE = "hotels_1k_llm.json"
MAX_RETRIES = 5
BATCH_SIZE = 5  # Сколько отзывов генерировать за один запрос к LLM