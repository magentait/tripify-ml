import uuid
from qdrant_client.models import PointStruct
from .embeddings import ReviewEmbedder
from .qdrant_setup import get_client, ensure_collection, COLLECTION


def _review_to_text(comment: dict) -> str:
    """Склеивает куски отзыва в один текст для эмбеддинга."""
    parts = []
    if comment.get("good_part"):
        parts.append(f"Плюсы: {comment['good_part']}")
    if comment.get("bad_part"):
        parts.append(f"Минусы: {comment['bad_part']}")
    if comment.get("common_text"):
        parts.append(comment["common_text"])
    return " ".join(parts).strip()


def index_hotel_reviews(hotels: list[dict], batch_size: int = 256):
    embedder = ReviewEmbedder()
    client = get_client()
    ensure_collection(client, vector_size=embedder.dim)

    # 1. Собираем все отзывы в плоский список
    records = []
    for hotel in hotels:
        hid = hotel["hid"]
        for c in hotel.get("reviews", {}).get("comments", []):
            text = _review_to_text(c)
            if not text or len(text) < 10:
                continue
            records.append({
                "text": text,
                "payload": {
                    "hotel_id": hid,
                    "hotel_title": hotel.get("title"),
                    "country": hotel.get("country"),
                    "rating": c.get("rating"),
                    "vacation_type": c.get("vacation_type"),
                    "author_country": c.get("country"),
                    "review_date": c.get("review_date"),
                    "text": text,
                },
            })

    if not records:
        print("Нет отзывов для индексации")
        return

    print(f"Индексация {len(records)} отзывов...")

    # 2. Батчами: эмбеддинг + upsert
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        texts = [r["text"] for r in batch]
        vectors = embedder.encode(texts)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec.tolist(),
                payload=r["payload"],
            )
            for r, vec in zip(batch, vectors)
        ]
        client.upsert(collection_name=COLLECTION, points=points)
        print(f"  загружено {min(i + batch_size, len(records))}/{len(records)}")

    print("✅ Готово")