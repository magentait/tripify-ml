"""
Основной скрипт генерации 1000 отелей.

Запуск:
    python generate.py
"""

import json
import time
import random
from config import TOTAL_HOTELS, OUTPUT_FILE, COMMENTS_PER_HOTEL
from hotel_generator import REAL_HOTELS, generate_hotel

random.seed(42)


def main():
    print(f"🏨 Генерация {TOTAL_HOTELS} отелей с {COMMENTS_PER_HOTEL} отзывами каждый")
    print(f"   Базовых шаблонов: {len(REAL_HOTELS)}")
    print(f"   Вариаций на шаблон: ~{TOTAL_HOTELS // len(REAL_HOTELS)}")
    print()

    hotels = []
    start_time = time.time()

    for i in range(TOTAL_HOTELS):
        # Циклически выбираем шаблон
        template = REAL_HOTELS[i % len(REAL_HOTELS)]
        variant = i // len(REAL_HOTELS)

        try:
            hotel = generate_hotel(template, variant, COMMENTS_PER_HOTEL)
            hotels.append(hotel)
        except Exception as e:
            print(f"  ❌ Ошибка при генерации отеля #{i}: {e}")
            continue

        # Прогресс
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (TOTAL_HOTELS - i - 1) / rate
            print(f"\n{'='*60}")
            print(f"📊 Прогресс: {i + 1}/{TOTAL_HOTELS} "
                  f"({(i+1)/TOTAL_HOTELS*100:.1f}%) | "
                  f"⏱ {elapsed:.0f}с | "
                  f"ETA: {eta:.0f}с")
            print(f"{'='*60}\n")

    # Финальная структура
    payload = {
        "hotels": hotels,
        "provider_id": 1,
        "provider_name": "Tripify",
        "total_hotels": len(hotels),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    file_size_mb = len(json.dumps(payload, ensure_ascii=False).encode()) / 1024 / 1024

    print(f"\n{'='*60}")
    print(f"✅ Готово!")
    print(f"   Отелей: {len(hotels)}")
    print(f"   Отзывов: {sum(len(h['reviews']['comments']) for h in hotels)}")
    print(f"   Файл: {OUTPUT_FILE} ({file_size_mb:.1f} MB)")
    print(f"   Время: {elapsed:.0f}с ({elapsed/60:.1f} мин)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()