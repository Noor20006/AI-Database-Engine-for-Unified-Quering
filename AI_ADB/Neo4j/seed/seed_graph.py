"""
SmartCRM — Neo4j Graph Seed Script
Member 2: Graph DB Engineer

Graph Model:
  (Customer)-[:FRIENDS_WITH]->(Customer)
  (Customer)-[:BOUGHT]->(Product)
  (Customer)-[:INFLUENCES]->(Customer)   ← derived from shared purchases

Seeds:
  200 Customer nodes
   30 Product nodes
  500 BOUGHT relationships
  300 FRIENDS_WITH relationships
  ~50 INFLUENCES relationships (high-spend → their friends)
"""

from neo4j import GraphDatabase
from faker import Faker
from dotenv import load_dotenv
import os
import random

load_dotenv()

fake = Faker()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URL"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)


def seed_data():
    with driver.session() as session:

        # ── 200 Customer Nodes ──────────────────────────────
        customer_ids = []
        for i in range(1, 201):
            name         = fake.name()
            total_spent  = round(random.uniform(0, 5000), 2)
            days_inactive = random.randint(0, 365)
            session.run("""
                MERGE (c:Customer {id: $id})
                SET c.name = $name,
                    c.total_spent = $total_spent,
                    c.days_inactive = $days_inactive
            """, id=i, name=name, total_spent=total_spent, days_inactive=days_inactive)
            customer_ids.append(i)
        print(f"✅ {len(customer_ids)} customers created")

        # ── 30 Product Nodes ────────────────────────────────
        categories  = ["Electronics", "Clothing", "Books", "Food", "Furniture"]
        product_ids = []
        for i in range(1, 31):
            name     = fake.word().capitalize() + " " + fake.word().capitalize()
            category = random.choice(categories)
            price    = round(random.uniform(5, 500), 2)
            session.run("""
                MERGE (p:Product {id: $id})
                SET p.name = $name, p.category = $category, p.price = $price
            """, id=i, name=name, category=category, price=price)
            product_ids.append(i)
        print(f"✅ {len(product_ids)} products created")

        # ── 500 BOUGHT Relationships ─────────────────────────
        for _ in range(500):
            cid = random.choice(customer_ids)
            pid = random.choice(product_ids)
            session.run("""
                MATCH (c:Customer {id: $cid})
                MATCH (p:Product  {id: $pid})
                MERGE (c)-[:BOUGHT]->(p)
            """, cid=cid, pid=pid)
        print("✅ 500 BOUGHT relationships created")

        # ── 300 FRIENDS_WITH Relationships ───────────────────
        for _ in range(300):
            id1 = random.choice(customer_ids)
            id2 = random.choice(customer_ids)
            if id1 != id2:
                session.run("""
                    MATCH (a:Customer {id: $id1})
                    MATCH (b:Customer {id: $id2})
                    MERGE (a)-[:FRIENDS_WITH]->(b)
                """, id1=id1, id2=id2)
        print("✅ 300 FRIENDS_WITH relationships created")

        # ── INFLUENCES: high-spender → their friends ─────────
        # High spenders are customers with total_spent > 3000
        result = session.run("""
            MATCH (c:Customer)
            WHERE c.total_spent > 3000
            RETURN c.id AS id
        """)
        high_spenders = [r["id"] for r in result]

        for hid in high_spenders:
            friends_result = session.run("""
                MATCH (h:Customer {id: $hid})-[:FRIENDS_WITH]->(f:Customer)
                RETURN f.id AS fid
            """, hid=hid)
            friends = [r["fid"] for r in friends_result]
            for fid in friends:
                session.run("""
                    MATCH (h:Customer {id: $hid})
                    MATCH (f:Customer {id: $fid})
                    MERGE (h)-[:INFLUENCES]->(f)
                """, hid=hid, fid=fid)

        print(f"✅ INFLUENCES relationships created from {len(high_spenders)} high-spend customers")


seed_data()
driver.close()
print("🎉 Neo4j seeding complete!")
