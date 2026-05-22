"""
SmartCRM — PostgreSQL Seed Script
Member 1: Database Engineer

Seeds: 200 customers, 30 products, 500 orders
Also syncs order_count on each customer for ML features.
"""

import psycopg2
import random
from faker import Faker
from dotenv import load_dotenv
import os
from datetime import date, timedelta

load_dotenv()

fake = Faker()
conn = psycopg2.connect(os.getenv("POSTGRES_URL"))
cur = conn.cursor()

# ── Products ────────────────────────────────────────────────
categories = ["Electronics", "Clothing", "Books", "Food", "Furniture"]
products = []
product_data = []

for _ in range(30):
    name     = fake.word().capitalize() + " " + fake.word().capitalize()
    category = random.choice(categories)
    price    = round(random.uniform(5, 500), 2)
    cur.execute(
        "INSERT INTO products (name, category, price) VALUES (%s, %s, %s) RETURNING id",
        (name, category, price)
    )
    pid = cur.fetchone()[0]
    products.append(pid)
    product_data.append({"id": pid, "name": name, "category": category, "price": price})

print(f"✅ {len(products)} products seeded")

# ── Customers ───────────────────────────────────────────────
customers = []
for _ in range(200):
    name        = fake.name()
    email       = fake.unique.email()
    last_active = date.today() - timedelta(days=random.randint(0, 365))
    total_spent = round(random.uniform(0, 5000), 2)
    cur.execute(
        """INSERT INTO customers (name, email, last_active, total_spent)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (name, email, last_active, total_spent)
    )
    customers.append(cur.fetchone()[0])

print(f"✅ {len(customers)} customers seeded")

# ── Orders ──────────────────────────────────────────────────
for _ in range(500):
    customer_id  = random.choice(customers)
    product_id   = random.choice(products)
    amount       = round(random.uniform(10, 500), 2)
    order_date   = date.today() - timedelta(days=random.randint(0, 365))
    cur.execute(
        "INSERT INTO orders (customer_id, product_id, amount, date) VALUES (%s, %s, %s, %s)",
        (customer_id, product_id, amount, order_date)
    )

print("✅ 500 orders seeded")

# ── Sync order_count on customers ───────────────────────────
cur.execute("""
    UPDATE customers c
    SET order_count = sub.cnt
    FROM (
        SELECT customer_id, COUNT(*) AS cnt
        FROM orders GROUP BY customer_id
    ) sub
    WHERE c.id = sub.customer_id
""")

conn.commit()
cur.close()
conn.close()
print("🎉 PostgreSQL seeding complete: 200 customers | 30 products | 500 orders")
