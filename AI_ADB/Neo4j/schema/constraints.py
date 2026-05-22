"""
SmartCRM — Neo4j Schema & Constraints
Member 2: Graph DB Engineer

Run this BEFORE seeding.
Creates uniqueness constraints and indexes.
"""

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URL"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)


def create_constraints():
    with driver.session() as session:

        # Uniqueness constraints
        session.run("""
            CREATE CONSTRAINT IF NOT EXISTS
            FOR (c:Customer) REQUIRE c.id IS UNIQUE
        """)
        session.run("""
            CREATE CONSTRAINT IF NOT EXISTS
            FOR (p:Product) REQUIRE p.id IS UNIQUE
        """)

        # Indexes for fast lookup
        session.run("""
            CREATE INDEX customer_name IF NOT EXISTS
            FOR (c:Customer) ON (c.name)
        """)
        session.run("""
            CREATE INDEX product_category IF NOT EXISTS
            FOR (p:Product) ON (p.category)
        """)

    print("✅ Constraints and indexes created!")


create_constraints()
driver.close()
