"""
Генерирует синтетические отели и загружает их отзывы в Qdrant.
Запуск:  python build_search_index.py
"""
import random
import numpy as np
from ranking.data_generator import SyntheticHotelGenerator
from search.indexer import index_hotel_reviews


def main():
    gen = SyntheticHotelGenerator()
    rng = random.Random(42)
    np_rng = np.random.RandomState(42)

    hotels = []
    user_ctx = gen._random_user_context(rng)
    for _ in range(50):
        hotel = gen._random_hotel(rng, np_rng, user_ctx)
        hotels.append(hotel)

    total_comments = sum(len(h["reviews"]["comments"]) for h in hotels)
    print(f"Сгенерировано {len(hotels)} отелей, всего {total_comments} отзывов")

    index_hotel_reviews(hotels)


if __name__ == "__main__":
    main()