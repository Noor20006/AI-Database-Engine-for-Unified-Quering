"""
SmartCRM — Neo4j Service Layer
Member 2: Graph DB Engineer

All functions return plain dicts for easy JSON serialization.
"""

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URL"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)


# ── Friend Queries ───────────────────────────────────────────

def get_friends_of_customer(customer_id: int):
    """Direct friends of a customer."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer {id: $id})-[:FRIENDS_WITH]->(friend:Customer)
            RETURN friend.id AS id, friend.name AS name,
                   friend.total_spent AS total_spent
        """, id=customer_id)
        return [dict(r) for r in result]


def get_friends_of_friends(customer_id: int):
    """2-hop friend discovery — shows graph power."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer {id: $id})-[:FRIENDS_WITH*2]->(fof:Customer)
            WHERE fof.id <> $id
            RETURN DISTINCT fof.id AS id, fof.name AS name
            LIMIT 20
        """, id=customer_id)
        return [dict(r) for r in result]


# ── Influence Queries ────────────────────────────────────────

def get_influential_customers(limit: int = 10):
    """Top influencers: customers with most friends."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer)-[:FRIENDS_WITH]->(friend:Customer)
            RETURN c.id AS id, c.name AS name,
                   COUNT(friend) AS friend_count,
                   c.total_spent AS total_spent
            ORDER BY friend_count DESC
            LIMIT $limit
        """, limit=limit)
        return [dict(r) for r in result]


def get_customers_influenced_by(customer_id: int):
    """Who does this customer influence via INFLUENCES edge."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer {id: $id})-[:INFLUENCES]->(target:Customer)
            RETURN target.id AS id, target.name AS name
        """, id=customer_id)
        return [dict(r) for r in result]


# ── Purchase Graph Queries ───────────────────────────────────

def get_customers_who_bought(category: str):
    """Graph-based: customers who bought a product category."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer)-[:BOUGHT]->(p:Product)
            WHERE toLower(p.category) = toLower($category)
            RETURN DISTINCT c.id AS id, c.name AS name,
                   c.total_spent AS total_spent
            ORDER BY c.total_spent DESC
        """, category=category)
        return [dict(r) for r in result]


def get_product_recommendations(customer_id: int):
    """
    Collaborative filtering via graph:
    'Products bought by my friends that I haven't bought yet.'
    """
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer {id: $id})-[:FRIENDS_WITH]->(friend:Customer)
            MATCH (friend)-[:BOUGHT]->(p:Product)
            WHERE NOT (c)-[:BOUGHT]->(p)
            RETURN DISTINCT p.id AS id, p.name AS name,
                   p.category AS category,
                   COUNT(friend) AS recommended_by_count
            ORDER BY recommended_by_count DESC
            LIMIT 10
        """, id=customer_id)
        return [dict(r) for r in result]


def get_churn_risk_network(customer_id: int):
    """
    AI Social Intelligence:
    Check if a customer's friends are inactive — raises churn risk.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer {id: $id})-[:FRIENDS_WITH]->(friend:Customer)
            WHERE friend.days_inactive > 60
            RETURN COUNT(friend) AS inactive_friends,
                   COLLECT(friend.name)[..5] AS sample_names
        """, id=customer_id)
        return [dict(r) for r in result]


def get_community_stats():
    """Summary stats about the graph."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Customer)
            OPTIONAL MATCH (c)-[:FRIENDS_WITH]->(f)
            OPTIONAL MATCH (c)-[:BOUGHT]->(p)
            RETURN
                COUNT(DISTINCT c) AS total_customers,
                COUNT(DISTINCT f) AS total_friendships,
                COUNT(DISTINCT p) AS total_purchases
        """)
        return [dict(r) for r in result]
