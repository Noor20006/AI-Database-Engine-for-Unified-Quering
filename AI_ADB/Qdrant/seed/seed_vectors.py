"""
SmartCRM — Qdrant Seed / Embedding Pipeline
Member 3: Vector DB + AI Router Engineer

Reads customer features from PostgreSQL, generates normalized
behavioral embeddings, and stores them in Qdrant.

Embedding strategy (no GPU, no heavy models):
  Features → normalize → pad to 128-dim vector

This is intentional: for a student project, a clean
hand-crafted feature vector is MORE explainable than
a black-box sentence-transformer.
"""

import os
import random
import math
import psycopg2
import psycopg2.extras
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from dotenv import load_dotenv

load_dotenv()

pg_conn = psycopg2.connect(
    os.getenv("POSTGRES_URL"),
    cursor_factory=psycopg2.extras.RealDictCursor
)
pg_cur = pg_conn.cursor()

qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

VECTOR_SIZE = 128


def build_customer_vector(row: dict) -> list[float]:
    """
    Build a normalized 128-dim behavioral embedding from customer features.
    First 3 dims encode real features; rest are noise padding for demo.
    """
    total_spent    = float(row["total_spent"] or 0)
    days_inactive  = float(row["days_inactive"] or 0)
    order_count    = float(row["order_count"] or 0)

    # Normalize to [0, 1]
    f1 = min(total_spent / 5000.0, 1.0)
    f2 = min(days_inactive / 365.0, 1.0)
    f3 = min(order_count / 20.0, 1.0)

    # Churn risk score as 4th dim
    if days_inactive > 90 and total_spent < 100:
        churn_score = 1.0
    elif days_inactive > 60 and total_spent < 300:
        churn_score = 0.6
    else:
        churn_score = 0.1

    core = [f1, f2, f3, churn_score]

    # Pad to VECTOR_SIZE with deterministic pseudo-noise from customer id
    random.seed(row["id"])
    padding = [random.gauss(0.5, 0.15) for _ in range(VECTOR_SIZE - len(core))]
    vector  = core + padding

    # L2 normalize
    magnitude = math.sqrt(sum(v * v for v in vector))
    return [v / magnitude for v in vector]


# ── Fetch customer features ──────────────────────────────────
pg_cur.execute("""
    SELECT id, name, email, total_spent, days_inactive, order_count, churn_risk
    FROM churn_features
    ORDER BY id
""")
customers = pg_cur.fetchall()

points = []
for row in customers:
    row = dict(row)
    vector = build_customer_vector(row)
    points.append(PointStruct(
        id=row["id"],
        vector=vector,
        payload={
            "name":         row["name"],
            "email":        row["email"],
            "total_spent":  float(row["total_spent"] or 0),
            "days_inactive": int(row["days_inactive"] or 0),
            "order_count":  int(row["order_count"] or 0),
            "churn_risk":   row["churn_risk"]
        }
    ))

qdrant.upsert(collection_name="customers", points=points)
print(f"✅ {len(points)} customer embeddings stored in Qdrant")

# ── Seed product review embeddings (synthetic) ───────────────
from faker import Faker
fake = Faker()

review_points = []
for pid in range(1, 31):
    random.seed(pid + 10000)
    vector = [random.gauss(0.5, 0.2) for _ in range(VECTOR_SIZE)]
    magnitude = math.sqrt(sum(v * v for v in vector))
    vector = [v / magnitude for v in vector]

    review_points.append(PointStruct(
        id=pid,
        vector=vector,
        payload={
            "product_id": pid,
            "review_text": fake.sentence(nb_words=12),
            "sentiment":   random.choice(["positive", "neutral", "negative"]),
            "rating":      random.randint(1, 5)
        }
    ))

qdrant.upsert(collection_name="product_reviews", points=review_points)
print(f"✅ {len(review_points)} product review embeddings stored in Qdrant")

pg_cur.close()
pg_conn.close()
qdrant.close()
print("🎉 Qdrant seeding complete!")
