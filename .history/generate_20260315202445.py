"""
Параллельная генерация 1000 отелей.
"""

import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOTAL_HOTELS, OUTPUT_FILE, COMMENTS_PER_HOTEL, MAX_WORKERS
from hotel_generator import REAL_HOTELS, generate_hotel

random.seed(42)


def generate_one(args):
    """Обёртка для параллельного вызова."""
    index, template, variant, comments_count = args
    try:
        hotel = generate_hotel(template, variant, comments_count)
        return index, hotel, None
    except Exception as e:
        return index, None, str(e)


def main():
    print(f"🏨 Генерация {TOTAL_HOTELS} отелей")
    print(f"   Потоков: {MAX_WORKERS}")
    print(f"   Отзывов/отель: {COMMENTS_PER_HOTEL}")
    print(f"   Запросов к LLM: ~{TOTAL_HOTELS} (по 1 на отель)")
    print()

    # Подготовка задач
    tasks = []
    for i in range(TOTAL_HOTELS):
        template = REAL_HOTELS[i % len(REAL_HOTELS)]
        variant = i // len(REAL_HOTELS)
        tasks.append((i, template, variant, COMMENTS_PER_HOTEL))

    hotels = [None] * TOTAL_HOTELS
    done_count = 0
    error_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(generate_one, task): task for task in tasks}

        for future in as_completed(futures):
            index, hotel, error = future.result()
            done_count += 1

            if error:
                error_count += 1
                if error_count <= 10:
                    print(f"  ❌ Отель #{index}: {error}")
            else:
                hotels[index] = hotel

            # Прогресс каждые 50 отелей
            if done_count % 50 == 0 or done_count == TOTAL_HOTELS:
                elapsed = time.time() - start_time
                rate = done_count / elapsed
                eta = (TOTAL_HOTELS - done_count) / rate if rate > 0 else 0
                print(
                    f"📊 {done_count}/{TOTAL_HOTELS} "
                    f"({done_count/TOTAL_HOTELS*100:.0f}%) | "
                    f"⏱ {elapsed:.0f}с | "
                    f"ETA: {eta:.0f}с | "
                    f"❌ {error_count}"
                )

    # Убираем None (ошибки)
    hotels = [h for h in hotels if h is not None]

    payload = {
        "hotels": hotels,
        "provider_id": 1,
        "provider_name": "Tripify",
        "total_hotels": len(hotels),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    size_mb = len(json.dumps(payload, ensure_ascii=False).encode()) / 1024 / 1024

    print(f"\n{'='*60}")
    print(f"✅ Готово!")
    print(f"   Отелей: {len(hotels)}")
    print(f"   Отзывов: {sum(len(h['reviews']['comments']) for h in hotels)}")
    print(f"   Ошибки: {error_count}")
    print(f"   Файл: {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print(f"   Время: {elapsed:.0f}с ({elapsed/60:.1f} мин)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()