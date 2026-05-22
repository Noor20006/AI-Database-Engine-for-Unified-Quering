"""
SmartCRM — Qdrant Collection Setup
Member 3: Vector DB + AI Router Engineer

Creates two collections:
  1. customers       — behavioral embeddings
  2. product_reviews — review text embeddings
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv
import os

load_dotenv()

client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

VECTOR_SIZE = 128   # lightweight; no GPU needed


def create_collections():

    # ── Customer behavioral embeddings ──────────────────────
    client.recreate_collection(
        collection_name="customers",
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    print("✅ Collection 'customers' created")

    # ── Product review embeddings ───────────────────────────
    client.recreate_collection(
        collection_name="product_reviews",
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    print("✅ Collection 'product_reviews' created")


create_collections()
client.close()
