# QueryMind: Hybrid Database Engine

**QueryMind** is a natural-language query middleware over three different database engines: **PostgreSQL** (relational), **Neo4j** (graph), and **Qdrant** (vector). A semantic router turns a plain-English question into the right database operations, and the results come back as one JSON response. The demo domain is a CRM (customers, orders, friendships, churn risk).

> *"Who are our top 5 spending customers?"* → PostgreSQL
> *"Show customers at high risk of churn."* → PostgreSQL + Neo4j + Qdrant
> *"Recommend products for customer ID 7."* → Neo4j
> *"Find customers with buying behaviors similar to ID 3."* → Qdrant

Advanced Database Management System Lab project, Department of Computer Science, University of Engineering and Technology (UET) Lahore. Session 2024–2028.

---

## The Problem

Modern systems use **polyglot persistence**: different database types for different data. But the engines are siloed, and answering one business question can require SQL, Cypher, and a vector search API, followed by manual joins in application code. Non-technical users are locked out. Commercial CRMs run on relational backends and can't do native graph traversal or vector similarity, and traditional federated databases add heavy configuration and no natural-language interface.

QueryMind adds one abstraction layer on top: the user states intent, and the system decides which engines to call and how to combine the results.

## Features

- **Tri-paradigm gateway:** relational, graph, and vector queries behind a single API.
- **Semantic routing:** natural-language queries are mapped to database execution plans, with an offline keyword-scoring router as a deterministic fallback.
- **Cross-database analytical joins:** for example, the *Social Churn Network* signal combines a Neo4j sub-graph traversal with PostgreSQL transactional filters.
- **Analytical views and precomputed features:** RFM-style features (`total_spent`, `days_inactive`, `order_count`) computed in PostgreSQL views.
- **Churn prediction:** a Random Forest classifier that predicts high / medium / low churn risk from those features.

## Architecture

```
                 natural-language query
                          │
                          ▼
              ┌───────────────────────┐
              │ router/query_router.py│  intent classification
              └───────────┬───────────┘  + parameter extraction
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  ┌───────────┐     ┌───────────┐     ┌───────────┐
  │ PostgreSQL│     │   Neo4j   │     │  Qdrant   │
  │ views/SQL │     │  Cypher   │     │ HNSW/cos. │
  └───────────┘     └───────────┘     └───────────┘
        │
        ▼
  ┌───────────┐
  │ ml/       │  Random Forest churn model
  └───────────┘
                          ▼
              unified multi-source JSON response
```

Request flow:

1. **Ingestion:** the gateway receives the raw text query.
2. **Semantic parsing:** the router picks an intent and the databases to call, and extracts parameters (customer ID, category, risk level).
3. **Execution:** PostgreSQL (SQL over views), Neo4j (Cypher pattern matching), and Qdrant (vector similarity), in parallel where needed.
4. **Aggregation:** results are joined and returned as one JSON payload.

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Relational | PostgreSQL 15+ | Transactions, customer profiles, analytical views (RFM features) |
| Graph | Neo4j 5.x | Multi-hop traversals over `FRIENDS_WITH` and `BOUGHT` relationships via Cypher |
| Vector | Qdrant 1.x | 128-dimensional behavioral embeddings, HNSW index, cosine similarity |
| Gateway | FastAPI | Async data broker and execution manager |
| ML | scikit-learn (Random Forest), pickle | Churn risk classification |

## Project Structure

```
QueryMind/
├── Database/          # Relational engine layer
│   ├── schema/        # SQL DDL schemas and constraints
│   ├── seed/          # Transactional seed data
│   ├── services/      # PostgreSQL driver logic & connection pools
│   └── setup_db.py    # Relational initialization script
├── Neo4j/             # Graph engine layer
│   ├── schema/        # Node constraints and index declarations
│   ├── seed/          # Graph population scripts (Cypher)
│   └── services/      # Neo4j driver connection orchestrators
├── Qdrant/            # Vector engine layer
│   ├── collections/   # Collection configuration
│   ├── seed/          # Vector injection modules
│   └── services/      # Vector search services
├── router/
│   └── query_router.py  # Intent classification + parameter extraction
└── ml/
    └── churn_model.py   # Churn model training and inference
```

## Data Model

**PostgreSQL** stores the core entities (customers, orders, products) and a `churn_features` view exposing `total_spent`, `days_inactive`, `order_count`, and `churn_risk`.

**Neo4j** holds a property graph of customer and product nodes connected by `FRIENDS_WITH` and `BOUGHT` edges. It replaces SQL self-joins with native traversals, for example products bought by friends of friends.

**Qdrant** has two collections:

| Collection | Contents |
|---|---|
| `customers` | 128-dim behavioral vectors built from spend, inactivity, order count, and a churn score |
| `product_reviews` | 128-dim review embeddings with sentiment and rating payloads |

## Prerequisites

- Python 3.10+
- PostgreSQL 15+ on port 5432
- Neo4j 5.x on port 7687
- Qdrant on port 6333, for example: `docker run -p 6333:6333 qdrant/qdrant`

## Setup

### 1. Configure environment variables

Each component has its own `.env` file. Never commit real credentials; add `.env` to `.gitignore`.

**`Database/.env`**
```env
POSTGRES_URL=postgresql://<user>:<password>@localhost:5432/<dbname>
```

**`Neo4j/.env`**
```env
NEO4J_URL=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
```

**`Qdrant/.env`**
```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
POSTGRES_URL=postgresql://<user>:<password>@localhost:5432/<dbname>
```

The `ml/` script also reads `POSTGRES_URL` via `python-dotenv`, so keep it in the environment or in a `.env` file in the directory you run it from.

### 2. Install dependencies

```bash
pip install -r Database/requirements.txt
pip install -r Neo4j/requirements.txt
pip install -r Qdrant/requirements.txt
pip install scikit-learn numpy psycopg2-binary python-dotenv
```

### 3. Initialize the databases

Set up the databases in this order:

1. **PostgreSQL:** run `Database/setup_db.py` to apply the schema in `Database/schema/` and load the seed data from `Database/seed/`.
2. **Neo4j:** apply the constraints in `Neo4j/schema/`, then run the population scripts in `Neo4j/seed/`.
3. **Qdrant:** create the collections defined in `Qdrant/collections/`, then run the scripts in `Qdrant/seed/`.

### 4. Train the churn model

```bash
python ml/churn_model.py
```

This reads the `churn_features` view from PostgreSQL, trains a Random Forest (100 trees, max depth 5) on an 80/20 split, prints a classification report, and saves `churn_model.pkl` and `label_encoder.pkl` next to the script.

## Usage

### Query routing

```python
from router.query_router import route_query_dict

route_query_dict("Find customers similar to customer id 5")
# {
#   "intent": "find_similar",
#   "databases": ["qdrant"],
#   "params": {"customer_id": 5},
#   "confidence": 0.33,
#   "explanation": "Semantic similarity → Qdrant vector search"
# }
```

Run the built-in demo:

```bash
python router/query_router.py
```

### Supported Intents

| Intent | Example query | Databases |
|---|---|---|
| `find_similar` | "Find customers similar to customer id 5" | Qdrant |
| `churn_risk` | "Who is at high churn risk?" | PostgreSQL, Neo4j, Qdrant |
| `social_influence` | "Who are the most influential customers in the network?" | Neo4j |
| `purchase_history` | "Find customers who bought electronics" | PostgreSQL |
| `product_recommendation` | "Recommend products for customer id 12" | Neo4j, Qdrant |
| `top_customers` | "Show top 10 highest spenders" | PostgreSQL |
| `customer_search` | "Find customer named Alice" | PostgreSQL |
| `general` (fallback) | anything unmatched | PostgreSQL |

Extracted parameters: `customer_id` (for example `id 5`), `category` (Electronics, Clothing, Books, Food, Furniture), and `risk_level` (`high`, `medium`, or `low`; defaults to `high` for churn queries).

### Qdrant Service

| Function | Description |
|---|---|
| `find_similar_customers(customer_id, top_k=5)` | Customers with the most similar behavior (cosine similarity) |
| `find_high_risk_similar_customers(top_k=10)` | Customers closest to a high-churn prototype, filtered to `churn_risk = "high"` |
| `find_similar_products(product_id, top_k=5)` | Products with similar review embeddings |
| `get_qdrant_stats()` | Point counts per collection and vector size |

### Churn Prediction

```python
from ml.churn_model import predict_churn

predict_churn(total_spent=50, days_inactive=120, order_count=1)
# {"churn_risk": "high", "confidence": ..., "probabilities": {"high": ..., "low": ..., "medium": ...}}
```

`predict_churn_batch(customers)` does the same for a list of customer dicts.

## Example Use Cases

| Query | Execution path |
|---|---|
| "Who are our top 5 spending customers?" | Pure relational: an indexed select in PostgreSQL. |
| "Show customers at high risk of churn." | PostgreSQL views (precomputed features) cross-referenced with Neo4j social links, plus Qdrant similarity to a high-risk profile. |
| "Recommend products for customer ID 7." | Cypher traversal of `FRIENDS_WITH`, returning `BOUGHT` products the customer hasn't purchased. |
| "Find customers with buying behaviors similar to ID 3." | Fetch the customer's vector, then HNSW nearest-neighbor search in Qdrant. |

## How the Keyword Router Works

1. Lowercase the query and count keyword hits for each intent.
2. Pick the intent with the most hits (ties go to the earlier entry in `INTENT_MAP`).
3. Confidence = `min(hits / 3, 1.0)`.
4. Extract parameters with regex and keyword lookups.
5. If nothing matches, fall back to `general` → PostgreSQL with confidence 0.4.

## Limitations

- Keyword matching is substring-based, so short keywords like `like`, `top`, or `buy` can match inside other words, and each query gets a single intent.
- The churn model uses three features only; the graph and vector signals are not fed into it.
- Customer embeddings are hand-built from the same three features plus a rule-based churn score, padded to 128 dimensions. They are not learned embeddings.
- The Qdrant service uses `client.search`, which newer `qdrant-client` versions deprecate in favor of `query_points`. Pin your `qdrant-client` version.
- The dataset is a prototype seed dataset.

## Future Work

- **Access control and auditing:** role-based access at the gateway (Analyst, Admin, Engineer) mapped to database execution profiles.
- **Caching:** a Redis tier above the router to cache execution plans for recurring queries.
- **Scaling:** PostgreSQL master-replica setup and sharding, plus cluster partitioning for Neo4j and Qdrant.

