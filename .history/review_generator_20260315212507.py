"""Асинхронная генерация отзывов через LLM с retry."""

import random
from typing import Optional
from llm_client import AsyncLLMClient

VACATION_TYPES = ["family", "solo", "couple", "business", "friends"]
REVIEW_COUNTRIES = [
    "RU", "US", "GB", "DE", "FR", "AE", "TR", "IN",
    "CN", "JP", "BR", "AU", "KR", "IT", "ES", "EG",
]


def build_review_prompt(hotel_title, city, country, hotel_class, count):
    system_prompt = """You are a dataset generator for a hotel booking platform.
You generate realistic, diverse hotel reviews.

STRICT RULES:
1. Return ONLY a valid JSON array — no explanations, no markdown.
2. Each element: {"author","country","vacation_type","rating","good_part","bad_part","common_text"}
3. author: realistic first name matching reviewer's country
4. country: 2-letter ISO code (vary!)
5. vacation_type: one of ["family","solo","couple","business","friends"]
6. rating: float 1.0-10.0 (mostly 6-9, some 3-5 and 9.5-10)
7. good_part: 2-5 vivid sentences with specific details (room numbers, staff names, dishes)
8. bad_part: 1-2 sentences or null (~30% null)
9. common_text: summary or null (~50% null)
10. Vary writing styles. Some casual with typos. Reference real nearby landmarks."""

    user_prompt = f"""Generate exactly {count} reviews for:
Hotel: "{hotel_title}" | City: {city} | Country: {country} | Stars: {hotel_class}
Reviewer countries: {random.sample(REVIEW_COUNTRIES, k=min(count, len(REVIEW_COUNTRIES)))}
Return ONLY a JSON array of {count} objects."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def validate_review(review):
    # type: (dict) -> Optional[dict]
    if not isinstance(review, dict):
        return None
    if not all(k in review for k in ("author", "country", "vacation_type", "rating")):
        return None
    try:
        review["rating"] = round(max(1.0, min(10.0, float(review["rating"]))), 1)
    except (ValueError, TypeError):
        review["rating"] = round(random.uniform(6.0, 9.0), 1)
    if review.get("vacation_type") not in VACATION_TYPES:
        review["vacation_type"] = random.choice(VACATION_TYPES)
    review.setdefault("good_part", None)
    review.setdefault("bad_part", None)
    review.setdefault("common_text", None)
    return review


async def generate_reviews_async(llm, hotel_title, city, country, hotel_class, count):
    # type: (AsyncLLMClient, str, str, str, int, int) -> list
    """
    Генерирует count отзывов. 3 попытки на уровне бизнес-логики.
    """
    messages = build_review_prompt(hotel_title, city, country, hotel_class, count)

    for attempt in range(1, 4):
        result = await llm.request_json(messages, max_tokens=4096, temperature=0.95)

        if result is not None:
            # Разворачиваем если модель обернула в dict
            if isinstance(result, dict):
                for key in ("reviews", "data", "comments", "results"):
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break
                else:
                    result = [result]

            if isinstance(result, list):
                reviews = []
                for raw in result:
                    v = validate_review(raw)
                    if v:
                        reviews.append(v)

                if len(reviews) >= count * 0.5:  # хотя бы половину получили
                    # Добиваем если не хватает
                    while len(reviews) < count:
                        reviews.append(reviews[len(reviews) % len(reviews)].copy())
                    return reviews[:count]

                print(f"      ⚠️  Только {len(reviews)}/{count} валидных (попытка {attempt}/3)")
            else:
                print(f"      ⚠️  Неожиданный тип: {type(result)} (попытка {attempt}/3)")
        else:
            print(f"      ❌ LLM None (попытка {attempt}/3)")

    # Все 3 попытки провалились — заглушки
    print(f"      💀 Все попытки провалились для «{hotel_title}»")
    fallback = []
    for _ in range(count):
        fallback.append({
            "author": random.choice(["[Name58]", "[Name59]", "[Name60]", "Yuki", "Wei"]),
            "country": random.choice(REVIEW_COUNTRIES),
            "vacation_type": random.choice(VACATION_TYPES),
            "rating": round(random.uniform(5.0, 9.5), 1),
            "good_part": "Nice hotel, enjoyed our stay.",
            "bad_part": None,
            "common_text": None,
        })
    return fallback