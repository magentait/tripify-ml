"""Тест: генерация 8 отзывов для одного отеля через review_generator."""

import json
from review_generator import generate_reviews

print("📡 Генерирую 8 отзывов для The Plaza Hotel...")
print()

reviews = generate_reviews(
    hotel_title="The Plaza Hotel",
    city="New York",
    country="US",
    hotel_class=5,
    count=8,
)

print(f"\n=== РЕЗУЛЬТАТ: {len(reviews)} отзывов ===\n")

stub_count = 0
real_count = 0

for i, r in enumerate(reviews):
    is_stub = r.get("good_part") == "Nice hotel, enjoyed our stay."
    if is_stub:
        stub_count += 1
        print(f"  [{i+1}] ❌ ЗАГЛУШКА — {r['author']} ({r['country']})")
    else:
        real_count += 1
        print(f"  [{i+1}] ✅ ЖИВОЙ — {r['author']} ({r['country']}): {r['good_part'][:80]}...")

print(f"\n📊 Живых: {real_count}, Заглушек: {stub_count}")

if stub_count > 0:
    print("\n⚠️  Есть заглушки! Проблема в generate_reviews или LLM.")
else:
    print("\n✅ Все отзывы живые! Проблема была в параллельности.")