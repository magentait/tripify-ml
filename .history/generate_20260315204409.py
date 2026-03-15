"""Параллельная генерация 1000 уникальных отелей."""

import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOTAL_HOTELS, OUTPUT_FILE, COMMENTS_PER_HOTEL, MAX_WORKERS
from hotel_generator import (
    REAL_HOTELS, generate_hotel, generate_hotel_variations,
)

random.seed(42)


def prefetch_variations():
    """Шаг 1: генерируем 1000 уникальных отелей через LLM (20 запросов)."""
    all_templates = []
    per_base = TOTAL_HOTELS // len(REAL_HOTELS)  # 50 вариаций на шаблон

    print(f"🔄 Шаг 1: генерация {TOTAL_HOTELS} уникальных отелей из {len(REAL_HOTELS)} шаблонов...")
    print(f"   {per_base} вариаций на шаблон, {len(REAL_HOTELS)} запросов к LLM\n")

    for i, base in enumerate(REAL_HOTELS):
        print(f"  [{i+1}/{len(REAL_HOTELS)}] Генерирую вариации для «{base['title']}»...")
        variations = generate_hotel_variations(base, count=per_base)

        if variations:
            for v in variations:
                merged = dict(base)  # копия шаблона
                merged["title"] = v.get("title", base["title"])
                merged["description"] = v.get("description", base["description"])
                merged["address"] = v.get("address", base["address"])
                merged["lat"] = float(v.get("lat", base["lat"]))
                merged["lng"] = float(v.get("lng", base["lng"]))
                merged["price_range"] = (
                    int(v.get("price", base["price_range"][0])),
                    int(v.get("price", base["price_range"][1])),
                )
                all_templates.append(merged)
            print(f"    ✓ Получено {len(variations)} вариаций")
        else:
            print(f"    ⚠️  LLM не вернул вариации, дублирую оригинал {per_base} раз")
            for _ in range(per_base):
                all_templates.append(dict(base))

    # Добиваем если не хватает
    while len(all_templates) < TOTAL_HOTELS:
        all_templates.append(dict(random.choice(REAL_HOTELS)))

    print(f"\n✅ Подготовлено {len(all_templates)} уникальных шаблонов\n")
    return all_templates[:TOTAL_HOTELS]


def generate_one(args):
    index, template, comments_count = args
    try:
        hotel = generate_hotel(template, 0, comments_count)
        return index, hotel, None
    except Exception as e:
        return index, None, str(e)


def main():
    start_time = time.time()

    # Шаг 1: уникальные отели
    templates = prefetch_variations()

    step1_time = time.time() - start_time
    print(f"⏱  Шаг 1 занял {step1_time:.0f}с\n")

    # Шаг 2: параллельная генерация отзывов
    print(f"🔄 Шаг 2: генерация отзывов ({MAX_WORKERS} потоков)...\n")

    tasks = [(i, t, COMMENTS_PER_HOTEL) for i, t in enumerate(templates)]
    hotels = [None] * TOTAL_HOTELS
    done_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(generate_one, task): task for task in tasks}

        for future in as_completed(futures):
            index, hotel, error = future.result()
            done_count += 1

            if error:
                error_count += 1
                if error_count <= 10:
                    print(f"  ❌ #{index}: {error}")
            else:
                hotels[index] = hotel

            if done_count % 50 == 0 or done_count == TOTAL_HOTELS:
                elapsed = time.time() - start_time
                rate = done_count / (elapsed - step1_time) if elapsed > step1_time else 1
                eta = (TOTAL_HOTELS - done_count) / rate if rate > 0 else 0
                print(
                    f"📊 {done_count}/{TOTAL_HOTELS} "
                    f"({done_count/TOTAL_HOTELS*100:.0f}%) | "
                    f"⏱ {elapsed:.0f}с | ETA: {eta:.0f}с | ❌ {error_count}"
                )

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
    print(f"   Уникальных названий: {len(set(h['title'] for h in hotels))}")
    print(f"   Отзывов: {sum(len(h['reviews']['comments']) for h in hotels)}")
    print(f"   Ошибки: {error_count}")
    print(f"   Файл: {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print(f"   Время: {elapsed:.0f}с ({elapsed/60:.1f} мин)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()