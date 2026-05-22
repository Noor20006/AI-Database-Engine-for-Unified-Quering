"""
SmartCRM — Qdrant Service Layer
Member 3: Vector DB + AI Router Engineer

Provides similarity search over customer and product vectors.
"""

import os
import math
import random
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

load_dotenv()

VECTOR_SIZE = 128

client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)


def _build_customer_vector(total_spent: float, days_inactive: float,
                            order_count: float, seed: int = 42) -> list[float]:
    """Rebuild the same deterministic vector used during seeding."""
    f1 = min(total_spent / 5000.0, 1.0)
    f2 = min(days_inactive / 365.0, 1.0)
    f3 = min(order_count / 20.0, 1.0)
    if days_inactive > 90 and total_spent < 100:
        churn_score = 1.0
    elif days_inactive > 60 and total_spent < 300:
        churn_score = 0.6
    else:
        churn_score = 0.1

    core = [f1, f2, f3, churn_score]
    random.seed(seed)
    padding   = [random.gauss(0.5, 0.15) for _ in range(VECTOR_SIZE - len(core))]
    vector    = core + padding
    magnitude = math.sqrt(sum(v * v for v in vector))
    return [v / magnitude for v in vector]


def find_similar_customers(customer_id: int, top_k: int = 5):
    """
    Find customers most similar in behavior to a given customer.
    Uses cosine similarity on behavioral embeddings.
    """
    # Fetch the customer's own vector from Qdrant
    result = client.retrieve(
        collection_name="customers",
        ids=[customer_id],
        with_vectors=True
    )
    if not result:
        return {"error": f"Customer {customer_id} not found in Qdrant"}

    query_vector = result[0].vector

    hits = client.search(
        collection_name="customers",
        query_vector=query_vector,
        limit=top_k + 1  # +1 to exclude the customer themselves
    )

    return [
        {
            "id":           hit.id,
            "name":         hit.payload.get("name"),
            "email":        hit.payload.get("email"),
            "churn_risk":   hit.payload.get("churn_risk"),
            "total_spent":  hit.payload.get("total_spent"),
            "similarity":   round(hit.score, 4)
        }
        for hit in hits
        if hit.id != customer_id
    ][:top_k]


def find_high_risk_similar_customers(top_k: int = 10):
    """
    Find all customers similar to 'high churn risk' profile.
    Query vector = a high-risk prototype embedding.
    """
    query_vector = _build_customer_vector(
        total_spent=50, days_inactive=120, order_count=1, seed=9999
    )

    hits = client.search(
        collection_name="customers",
        query_vector=query_vector,
        limit=top_k,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="churn_risk",
                    match=MatchValue(value="high")
                )
            ]
        )
    )

    return [
        {
            "id":           hit.id,
            "name":         hit.payload.get("name"),
            "churn_risk":   hit.payload.get("churn_risk"),
            "days_inactive": hit.payload.get("days_inactive"),
            "similarity":   round(hit.score, 4)
        }
        for hit in hits
    ]


def find_similar_products(product_id: int, top_k: int = 5):
    """Find semantically similar products by review embedding."""
    result = client.retrieve(
        collection_name="product_reviews",
        ids=[product_id],
        with_vectors=True
    )
    if not result:
        return {"error": f"Product {product_id} not found in Qdrant"}

    query_vector = result[0].vector

    hits = client.search(
        collection_name="product_reviews",
        query_vector=query_vector,
        limit=top_k + 1
    )

    return [
        {
            "product_id":  hit.id,
            "review_text": hit.payload.get("review_text"),
            "sentiment":   hit.payload.get("sentiment"),
            "rating":      hit.payload.get("rating"),
            "similarity":  round(hit.score, 4)
        }
        for hit in hits
        if hit.id != product_id
    ][:top_k]


def get_qdrant_stats():
    """Collection stats."""
    c_info = client.get_collection("customers")
    r_info = client.get_collection("product_reviews")
    return {
        "customers_vectors":       c_info.points_count,
        "product_review_vectors":  r_info.points_count,
        "vector_size":             VECTOR_SIZE
    }
