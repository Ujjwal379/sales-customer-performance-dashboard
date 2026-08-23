import pandas as pd
import requests
from sqlalchemy import create_engine

print("Fetching raw data from API...")
response = requests.get("https://dummyjson.com/carts?limit=50")
data = response.json()

orders_list = []
for cart in data["carts"]:
    for item in cart["products"]:
        orders_list.append(
            {
                "cart_id": cart["id"],
                "user_id": cart["userId"],
                "product_id": item["id"],
                "product_title": item["title"],
                "unit_price": item["price"],
                "quantity": item["quantity"],
                "item_total": item["total"],
                "discounted_total": item["discountedTotal"],
            }
        )

df = pd.DataFrame(orders_list)

# Transform
df["estimated_cost"] = df["unit_price"] * 0.6
df["cogs"] = df["estimated_cost"] * df["quantity"]
df["profit"] = df["discounted_total"] - df["cogs"]
df["profit_margin_pct"] = (df["profit"] / df["discounted_total"]) * 100

# 3. LOAD TO AIVEN POSTGRESQL USING PSYCOPG2 DIRECTLY
import psycopg2

print("Writing data to PostgreSQL...")

import os

# Database credentials (reads from GitHub Secrets or falls back to Aiven credentials)
host = os.getenv("DB_HOST", "sales-db-project-guptaujjwal379-cc5c.d.aivencloud.com")
port = os.getenv("DB_PORT", "25244")
dbname = os.getenv("DB_NAME", "defaultdb")
user = os.getenv("DB_USER", "avnadmin")
password = os.getenv("DB_PASSWORD", "AVNS_sqkx4vCc8alsbvnlyS0")

conn = psycopg2.connect(
    host=host,
    port=port,
    dbname=dbname,
    user=user,
    password=password,
    sslmode="require",
)

cursor = conn.cursor()

# Create table schema
create_table_sql = """
DROP TABLE IF EXISTS stg_sales_data;
CREATE TABLE stg_sales_data (
    cart_id INT,
    user_id INT,
    product_id INT,
    product_title TEXT,
    unit_price NUMERIC,
    quantity INT,
    item_total NUMERIC,
    discounted_total NUMERIC,
    estimated_cost NUMERIC,
    cogs NUMERIC,
    profit NUMERIC,
    profit_margin_pct NUMERIC
);
"""
cursor.execute("TRUNCATE TABLE stg_sales_data;")

# Insert rows directly
insert_sql = """
INSERT INTO stg_sales_data VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

for row in df.itertuples(index=False):
    cursor.execute(insert_sql, tuple(row))

conn.commit()
cursor.close()
conn.close()

print("Data pipeline executed successfully!")
