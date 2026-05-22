"""
SmartCRM — PostgreSQL Service Layer
Member 1: Database Engineer

All functions return plain dicts for easy JSON serialization
by the FastAPI layer (Member 4).
"""

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    return psycopg2.connect(
        os.getenv("POSTGRES_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )


# ── Churn Queries ────────────────────────────────────────────

def get_risky_customers(risk_level: str = "high", limit: int = 50):
    """
    Returns customers at a given churn risk level.
    Uses the churn_features view defined in init.sql.
    risk_level: 'high' | 'medium' | 'low'
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, name, email, total_spent, days_inactive, order_count, churn_risk
        FROM churn_features
        WHERE churn_risk = %s
        ORDER BY days_inactive DESC
        LIMIT %s;
    """, (risk_level, limit))
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


def get_all_churn_features():
    """Return all customers with churn features — used by ML model."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, name, email, total_spent, days_inactive, order_count, churn_risk
        FROM churn_features
        ORDER BY days_inactive DESC;
    """)
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


# ── Product / Order Queries ──────────────────────────────────

def get_customers_by_category(category: str):
    """Customers who bought from a given product category."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT DISTINCT c.id, c.name, c.email, c.total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        JOIN products p ON o.product_id = p.id
        WHERE LOWER(p.category) = LOWER(%s)
        ORDER BY c.total_spent DESC;
    """, (category,))
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


def get_top_spenders(limit: int = 10):
    """Top customers by total_spent."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, name, email, total_spent, order_count
        FROM customers
        ORDER BY total_spent DESC
        LIMIT %s;
    """, (limit,))
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


def get_orders_by_customer(customer_id: int):
    """Full order history for a specific customer."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT o.id, p.name AS product, p.category, o.amount, o.date
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.customer_id = %s
        ORDER BY o.date DESC;
    """, (customer_id,))
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


def search_customers(query: str):
    """Full-text search on customer name or email."""
    conn = get_connection()
    cur  = conn.cursor()
    like = f"%{query}%"
    cur.execute("""
        SELECT id, name, email, total_spent, order_count
        FROM customers
        WHERE LOWER(name) LIKE LOWER(%s)
           OR LOWER(email) LIKE LOWER(%s)
        LIMIT 20;
    """, (like, like))
    results = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in results]


def get_summary_stats():
    """Dashboard summary — total customers, orders, revenue."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            (SELECT COUNT(*)  FROM customers)              AS total_customers,
            (SELECT COUNT(*)  FROM orders)                 AS total_orders,
            (SELECT SUM(amount) FROM orders)               AS total_revenue,
            (SELECT COUNT(*) FROM churn_features
             WHERE churn_risk = 'high')                    AS high_risk_customers;
    """)
    result = cur.fetchone()
    cur.close(); conn.close()
    return dict(result)
