"""Асинхронная генерация 1000 отелей."""

import asyncio
import json
import time
import random
from config import TOTAL_HOTELS, OUTPUT_FILE, COMMENTS_PER_HOTEL, MAX_CONCURRENT
from llm_client import AsyncLLMClient
from hotel_generator import (
    REAL_HOTELS, generate_hotel_async, generate_hotel_variations_async,
)

random.seed(42)


async def prefetch_variations(llm):
    """Шаг 1: последовательно генерируем уникальные шаблоны (20 запросов)."""
    all_templates = []
    per_base = TOTAL_HOTELS // len(REAL_HOTELS)

    print(f"🔄 Шаг 1: генерация {TOTAL_HOTELS} уникальных отелей...")
    print(f"   {per_base} вариаций × {len(REAL_HOTELS)} шаблонов\n")

    for i, base in enumerate(REAL_HOTELS):
        print(f"  [{i+1}/{len(REAL_HOTELS)}] «{base['title']}»...", end=" ", flush=True)

        variations = await generate_hotel_variations_async(llm, base, count=per_base)

        if variations:
            for v in variations:
                merged = dict(base)
                merged["title"] = v.get("title", base["title"])
                merged["description"] = v.get("description", base["description"])
                merged["address"] = v.get("address", base["address"])
                try:
                    merged["lat"] = float(v.get("lat", base["lat"]))
                    merged["lng"] = float(v.get("lng", base["lng"]))
                except (ValueError, TypeError):
                    pass
                try:
                    p = int(v.get("price", base["price_range"][0]))
                    merged["price_range"] = (p, p)
                except (ValueError, TypeError):
                    pass
                hc = v.get("hotel_class", base["hotel_class"])
                try:
                    merged["hotel_class"] = max(1, min(5, int(hc)))
                except (ValueError, TypeError):
                    pass
                all_templates.append(merged)
            print(f"✓ {len(variations)}")
        else:
            print(f"⚠️  fallback")
            for _ in range(per_base):
                all_templates.append(dict(base))

    while len(all_templates) < TOTAL_HOTELS:
        all_templates.append(dict(random.choice(REAL_HOTELS)))

    return all_templates[:TOTAL_HOTELS]


async def generate_one(llm, index, template, comments_count):
    """Генерация одного отеля с логированием."""
    try:
        hotel = await generate_hotel_async(llm, template, comments_count)

        # Проверяем качество
        stubs = sum(
            1 for c in hotel["reviews"]["comments"]
            if c.get("good_part") == "Nice hotel, enjoyed our stay."
        )
        total = len(hotel["reviews"]["comments"])
        status = "✅" if stubs == 0 else f"⚠️ {stubs}/{total} заглушек"

        return index, hotel, None, status
    except Exception as e:
        return index, None, str(e), "❌"


async def main():
    start_time = time.time()

    llm = AsyncLLMClient(max_concurrent=MAX_CONCURRENT)

    try:
        # ── Шаг 1: уникальные отели ──
        templates = await prefetch_variations(llm)
        step1_time = time.time() - start_time
        print(f"\n⏱  Шаг 1: {step1_time:.0f}с ({step1_time/60:.1f} мин)\n")

        # ── Шаг 2: параллельная генерация отзывов ──
        print(f"🔄 Шаг 2: генерация отзывов (async, {MAX_CONCURRENT} одновременно)...\n")

        tasks = [
            generate_one(llm, i, t, COMMENTS_PER_HOTEL)
            for i, t in enumerate(templates)
        ]

        hotels = [None] * TOTAL_HOTELS
        done = 0
        errors = 0
        stubs_total = 0

        for coro in asyncio.as_completed(tasks):
            index, hotel, error, status = await coro
            done += 1

            if error:
                errors += 1
                if errors <= 5:
                    print(f"  ❌ #{index}: {error}")
            else:
                hotels[index] = hotel
                if "⚠️" in status:
                    stubs_total += 1

            if done % 50 == 0 or done == TOTAL_HOTELS:
                elapsed = time.time() - start_time
                step2_elapsed = elapsed - step1_time
                rate = done / step2_elapsed if step2_elapsed > 0 else 1
                eta = (TOTAL_HOTELS - done) / rate if rate > 0 else 0
                print(
                    f"📊 {done}/{TOTAL_HOTELS} "
                    f"({done/TOTAL_HOTELS*100:.0f}%) | "
                    f"⏱ {elapsed:.0f}с | "
                    f"ETA: {eta:.0f}с ({eta/60:.1f} мин) | "
                    f"❌ {errors} | ⚠️  {stubs_total} с заглушками"
                )

    finally:
        await llm.close()

    # ── Сохранение ──
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
    total_reviews = sum(len(h["reviews"]["comments"]) for h in hotels)
    unique_titles = len(set(h["title"] for h in hotels))

    print(f"\n{'='*60}")
    print(f"✅ Готово!")
    print(f"   Отелей: {len(hotels)}")
    print(f"   Уникальных названий: {unique_titles}")
    print(f"   Отзывов: {total_reviews}")
    print(f"   Ошибки: {errors}")
    print(f"   С заглушками: {stubs_total}")
    print(f"   Файл: {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print(f"   Время: {elapsed:.0f}с ({elapsed/60:.1f} мин)")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())