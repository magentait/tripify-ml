"""
Генерация реалистичных отзывов через LLM.
"""

import random
from llm_client import LLMClient
from config import BATCH_SIZE
from typing import Optional

client = LLMClient()

VACATION_TYPES = ["family", "solo", "couple", "business", "friends"]
REVIEW_COUNTRIES = [
    "RU", "US", "GB", "DE", "FR", "AE", "TR", "IN",
    "CN", "JP", "BR", "AU", "KR", "IT", "ES", "EG",
    "NL", "SE", "NO", "PL", "CZ", "AR", "MX", "TH",
]


def build_review_prompt(hotel_title: str, city: str, country: str,
                        hotel_class: int, count: int,
                        batch_index: int = 0) -> list:
    """
    Формирует prompt для генерации батча отзывов.
    batch_index используется для разнообразия между батчами.
    """

    # Варьируем "настроение" батча
    mood_hints = [
        "Mix of very positive and mildly critical reviews.",
        "Mostly positive with one disappointed guest.",
        "Enthusiastic reviews from different types of travelers.",
        "Balanced mix — some loved it, some found issues.",
        "Predominantly great reviews with detailed specific praise.",
    ]
    mood = mood_hints[batch_index % len(mood_hints)]

    system_prompt = """You are a dataset generator for a hotel booking platform.
You generate realistic, diverse hotel reviews that read like real guests wrote them.

STRICT RULES:
1. Return ONLY a valid JSON array — no explanations, no markdown fences.
2. Each element must be a JSON object with EXACTLY these fields:
   - "author" (string): realistic first name matching the reviewer's country
   - "country" (string): 2-letter ISO country code
   - "vacation_type" (string): one of ["family", "solo", "couple", "business", "friends"]
   - "rating" (number): float from 1.0 to 10.0
   - "good_part" (string or null): 2-5 sentences about positives
   - "bad_part" (string or null): 1-2 sentences about negatives, or null
   - "common_text" (string or null): general summary sentence, or null
3. ~30% of bad_part should be null, ~50% of common_text should be null.
4. Vary reviewer countries, vacation types, writing styles, and detail levels.
5. Include specific details: room numbers, staff names, dish names, floor levels.
6. Some reviews should have minor typos or casual tone.
7. Reference real landmarks and neighborhoods near the hotel.
8. Ratings distribution: mostly 6-9, occasional 3-5 and 9.5-10."""

    user_prompt = f"""Generate exactly {count} hotel reviews for:

Hotel: "{hotel_title}"
City: {city}
Country: {country}
Stars: {hotel_class}

Mood hint: {mood}

Reviewer countries to use in this batch (pick from these):
{random.sample(REVIEW_COUNTRIES, k=min(count + 2, len(REVIEW_COUNTRIES)))}

Vacation types to cover: {random.sample(VACATION_TYPES, k=min(count, len(VACATION_TYPES)))}

Return ONLY a JSON array of {count} objects. No markdown, no explanation."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def validate_review(review: dict) -> Optional[dict]:
    """Валидирует и нормализует один отзыв."""
    required = {"author", "country", "vacation_type", "rating"}

    if not isinstance(review, dict):
        return None

    # Проверяем обязательные поля
    if not all(k in review for k in required):
        return None

    # Нормализуем
    try:
        review["rating"] = round(float(review["rating"]), 1)
        review["rating"] = max(1.0, min(10.0, review["rating"]))
    except (ValueError, TypeError):
        review["rating"] = round(random.uniform(6.0, 9.0), 1)

    if review.get("vacation_type") not in VACATION_TYPES:
        review["vacation_type"] = random.choice(VACATION_TYPES)

    if not isinstance(review.get("country"), str) or len(review["country"]) != 2:
        review["country"] = random.choice(REVIEW_COUNTRIES)

    # Гарантируем наличие всех полей
    review.setdefault("good_part", None)
    review.setdefault("bad_part", None)
    review.setdefault("common_text", None)

    return review


def generate_reviews(hotel_title: str, city: str, country: str,
                     hotel_class: int, count: int) -> list:
    """
    Генерирует count отзывов, обращаясь к LLM батчами.

    Returns:
        list[dict]: Список валидированных отзывов
    """
    all_reviews = []
    generated = 0
    batch_index = 0
    max_attempts = (count // BATCH_SIZE + 1) * 3  # защита от бесконечного цикла
    attempts = 0

    while generated < count and attempts < max_attempts:
        attempts += 1
        batch_count = min(BATCH_SIZE, count - generated)

        messages = build_review_prompt(
            hotel_title=hotel_title,
            city=city,
            country=country,
            hotel_class=hotel_class,
            count=batch_count,
            batch_index=batch_index,
        )

        result = client.request_json(messages, max_tokens=4096, temperature=0.95)

        if result is None:
            print(f"    ⚠️  LLM вернул None для батча {batch_index}, пропускаем")
            batch_index += 1
            continue

        # result может быть списком или словарём
        if isinstance(result, dict):
            # Иногда модель возвращает {"reviews": [...]}
            for key in ("reviews", "data", "comments", "results"):
                if key in result and isinstance(result[key], list):
                    result = result[key]
                    break
            else:
                result = [result]

        if not isinstance(result, list):
            print(f"    ⚠️  Неожиданный тип ответа: {type(result)}")
            batch_index += 1
            continue

        for raw_review in result:
            validated = validate_review(raw_review)
            if validated:
                all_reviews.append(validated)
                generated += 1
                if generated >= count:
                    break

        batch_index += 1
        print(f"    ✓ Батч {batch_index}: получено {len(result)} отзывов, "
              f"всего {generated}/{count}")

    if generated < count:
        print(f"    ⚠️  Сгенерировано {generated}/{count} отзывов")

    return all_reviews