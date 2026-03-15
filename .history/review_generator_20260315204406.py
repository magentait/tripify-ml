"""Генерация отзывов через LLM — один запрос на отель."""

import random
from typing import Optional
from llm_client import LLMClient
from config import BATCH_SIZE

client = LLMClient()

VACATION_TYPES = ["family", "solo", "couple", "business", "friends"]
REVIEW_COUNTRIES = [
    "RU", "US", "GB", "DE", "FR", "AE", "TR", "IN",
    "CN", "JP", "BR", "AU", "KR", "IT", "ES", "EG",
]


def build_review_prompt(hotel_title, city, country, hotel_class, count):
    system_prompt = """You are a dataset generator for a hotel booking platform.
You generate realistic, diverse hotel reviews that read like real guests wrote them.

STRICT RULES:
1. Return ONLY a valid JSON array — no explanations, no markdown fences.
2. Each element must have EXACTLY these fields:
   - "author" (string): realistic first name matching reviewer's country
   - "country" (string): 2-letter ISO code
   - "vacation_type" (string): one of ["family","solo","couple","business","friends"]
   - "rating" (number): float 1.0-10.0
   - "good_part" (string or null): 2-5 sentences about positives
   - "bad_part" (string or null): 1-2 sentences or null (~30% null)
   - "common_text" (string or null): summary or null (~50% null)
3. Include specific details: room numbers, staff names, dish names.
4. Vary countries, styles, detail levels. Some casual with typos.
5. Ratings: mostly 6-9, occasional 3-5 and 9.5-10."""

    user_prompt = f"""Generate exactly {count} reviews for:
Hotel: "{hotel_title}" | City: {city} | Country: {country} | Stars: {hotel_class}
Use these reviewer countries: {random.sample(REVIEW_COUNTRIES, k=min(count, len(REVIEW_COUNTRIES)))}
Cover vacation types: {VACATION_TYPES}
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


def generate_reviews(hotel_title, city, country, hotel_class, count):
    messages = build_review_prompt(hotel_title, city, country, hotel_class, count)
    result = client.request_json(messages, max_tokens=4096, temperature=0.95)

    reviews = []

    if result is None:
        print(f"    ❌ LLM вернул None для «{hotel_title}» — все отзывы будут заглушками!")
    elif isinstance(result, dict):
        for key in ("reviews", "data", "comments", "results"):
            if key in result and isinstance(result[key], list):
                result = result[key]
                break
        else:
            result = [result]

    if isinstance(result, list):
        for raw in result:
            v = validate_review(raw)
            if v:
                reviews.append(v)

    if len(reviews) < count:
        print(f"    ⚠️  LLM дал {len(reviews)}/{count} для «{hotel_title}», добиваю заглушками")

    while len(reviews) < count:
        reviews.append({
            "author": random.choice(["Anna", "Maria", "John", "Yuki", "Wei"]),
            "country": random.choice(REVIEW_COUNTRIES),
            "vacation_type": random.choice(VACATION_TYPES),
            "rating": round(random.uniform(5.0, 9.5), 1),
            "good_part": "Nice hotel, enjoyed our stay.",
            "bad_part": None,
            "common_text": None,
        })

    return reviews[:count]