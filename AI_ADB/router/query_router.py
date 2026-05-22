"""
SmartCRM — AI Query Router
Member 3: Vector DB + AI Router Engineer

THE CORE INNOVATION of the project.

Takes a natural language query and decides:
  1. Which databases to route to
  2. What intent the query represents
  3. What parameters to extract

This is the "intelligence brain" of SmartCRM.
"""

import re
from dataclasses import dataclass, field


@dataclass
class RouterResult:
    intent:    str
    databases: list[str]
    params:    dict = field(default_factory=dict)
    confidence: float = 1.0
    explanation: str = ""


# ── Intent Definitions ───────────────────────────────────────
#
# Each intent has:
#   keywords   — triggers that match this intent
#   databases  — which DBs to call
#   params     — how to extract parameters from the query
#

INTENT_MAP = [
    {
        "intent":    "find_similar",
        "keywords":  ["similar", "like", "resemble", "behave like", "looks like"],
        "databases": ["qdrant"],
        "explanation": "Semantic similarity → Qdrant vector search"
    },
    {
        "intent":    "churn_risk",
        "keywords":  ["churn", "risk", "leaving", "inactive", "at risk", "losing",
                      "churning", "likely to leave"],
        "databases": ["postgres", "neo4j", "qdrant"],
        "explanation": "Churn prediction → Postgres (features) + Neo4j (social graph) + Qdrant (similarity)"
    },
    {
        "intent":    "social_influence",
        "keywords":  ["friend", "influence", "network", "social", "connected",
                      "community", "who knows", "relationship"],
        "databases": ["neo4j"],
        "explanation": "Social graph traversal → Neo4j"
    },
    {
        "intent":    "purchase_history",
        "keywords":  ["bought", "order", "purchase", "spent", "buy", "transaction",
                      "history", "product"],
        "databases": ["postgres"],
        "explanation": "Transactional query → PostgreSQL"
    },
    {
        "intent":    "product_recommendation",
        "keywords":  ["recommend", "suggest", "what should", "next buy",
                      "popular among friends"],
        "databases": ["neo4j", "qdrant"],
        "explanation": "Collaborative filtering → Neo4j (friends bought) + Qdrant (similar users)"
    },
    {
        "intent":    "top_customers",
        "keywords":  ["top", "best", "highest", "most spent", "vip", "valuable"],
        "databases": ["postgres"],
        "explanation": "Ranking query → PostgreSQL"
    },
    {
        "intent":    "customer_search",
        "keywords":  ["find customer", "search customer", "who is", "customer named"],
        "databases": ["postgres"],
        "explanation": "Search → PostgreSQL full-text"
    },
]


# ── Parameter Extractors ─────────────────────────────────────

def _extract_customer_id(query: str) -> dict:
    """Extract numeric customer ID from query string."""
    match = re.search(r'\bid\s*[:=]?\s*(\d+)', query, re.IGNORECASE)
    if match:
        return {"customer_id": int(match.group(1))}
    return {}


def _extract_category(query: str) -> dict:
    """Extract product category if mentioned."""
    categories = ["electronics", "clothing", "books", "food", "furniture"]
    for cat in categories:
        if cat in query.lower():
            return {"category": cat.capitalize()}
    return {}


def _extract_risk_level(query: str) -> dict:
    """Extract churn risk level from query."""
    if "high" in query.lower():
        return {"risk_level": "high"}
    if "medium" in query.lower():
        return {"risk_level": "medium"}
    if "low" in query.lower():
        return {"risk_level": "low"}
    return {"risk_level": "high"}   # default


# ── Router Core ──────────────────────────────────────────────

def route_query(query: str) -> RouterResult:
    """
    Main routing function.

    Takes a natural language query string.
    Returns a RouterResult with intent, databases, and extracted params.
    """
    q_lower = query.lower()

    # Score each intent by keyword match count
    scores = []
    for entry in INTENT_MAP:
        score = sum(1 for kw in entry["keywords"] if kw in q_lower)
        if score > 0:
            scores.append((score, entry))

    if not scores:
        # Fallback: default to postgres if nothing matched
        return RouterResult(
            intent="general",
            databases=["postgres"],
            params={},
            confidence=0.4,
            explanation="No specific intent matched — defaulting to PostgreSQL"
        )

    # Pick highest-scoring intent
    scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_entry = scores[0]
    confidence = min(best_score / 3.0, 1.0)   # normalize to 0-1

    # Extract parameters
    params = {}
    params.update(_extract_customer_id(query))
    params.update(_extract_category(query))
    if best_entry["intent"] == "churn_risk":
        params.update(_extract_risk_level(query))

    return RouterResult(
        intent=best_entry["intent"],
        databases=best_entry["databases"],
        params=params,
        confidence=round(confidence, 2),
        explanation=best_entry["explanation"]
    )


def route_query_dict(query: str) -> dict:
    """Convenience wrapper — returns dict for JSON serialization."""
    result = route_query(query)
    return {
        "query":       query,
        "intent":      result.intent,
        "databases":   result.databases,
        "params":      result.params,
        "confidence":  result.confidence,
        "explanation": result.explanation
    }


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    test_queries = [
        "Find customers similar to customer id 5",
        "Who is at high churn risk?",
        "Who are the most influential customers in the network?",
        "Find customers who bought electronics",
        "Recommend products for customer id 12",
        "Show top 10 highest spenders",
        "Find customers who are leaving and have friends who also left"
    ]

    print("=" * 60)
    print("SmartCRM — AI Query Router Test")
    print("=" * 60)
    for q in test_queries:
        result = route_query_dict(q)
        print(f"\nQuery:       {q}")
        print(f"Intent:      {result['intent']}")
        print(f"Databases:   {result['databases']}")
        print(f"Params:      {result['params']}")
        print(f"Confidence:  {result['confidence']}")
        print(f"Explanation: {result['explanation']}")
