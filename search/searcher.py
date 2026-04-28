from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from .embeddings import ReviewEmbedder
from .qdrant_setup import get_client, COLLECTION


class ReviewSearcher:
    def __init__(self):
        self.embedder = ReviewEmbedder()
        self.client = get_client()

    def search(
        self,
        query: str,
        limit: int = 10,
        hotel_id: int | None = None,
        min_rating: float | None = None,
        vacation_type: str | None = None,
    ):
        vec = self.embedder.encode_query(query)

        # Собираем фильтр
        must = []
        if hotel_id is not None:
            must.append(FieldCondition(key="hotel_id", match=MatchValue(value=hotel_id)))
        if vacation_type:
            must.append(FieldCondition(key="vacation_type", match=MatchValue(value=vacation_type)))
        if min_rating is not None:
            must.append(FieldCondition(key="rating", range=Range(gte=min_rating)))

        qfilter = Filter(must=must) if must else None

        results = self.client.query_points(
            collection_name=COLLECTION,
            query=vec.tolist(),
            query_filter=qfilter,
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "score": r.score,
                "hotel_id": r.payload["hotel_id"],
                "text": r.payload["text"],
                "rating": r.payload.get("rating"),
                "vacation_type": r.payload.get("vacation_type"),
            }
            for r in results
        ]