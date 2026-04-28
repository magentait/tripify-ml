from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PayloadSchemaType
)

COLLECTION = "hotel_reviews"


def get_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    return QdrantClient(host=host, port=port)


def ensure_collection(client: QdrantClient, vector_size: int, recreate: bool = False):
    exists = client.collection_exists(COLLECTION)
    if exists and recreate:
        client.delete_collection(COLLECTION)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        # Индексы по payload — чтобы быстро фильтровать
        client.create_payload_index(COLLECTION, "hotel_id", PayloadSchemaType.INTEGER)
        client.create_payload_index(COLLECTION, "rating",   PayloadSchemaType.FLOAT)
        client.create_payload_index(COLLECTION, "language", PayloadSchemaType.KEYWORD)
        client.create_payload_index(COLLECTION, "vacation_type", PayloadSchemaType.KEYWORD)