import sqlite3
import pandas as pd
import numpy as np
import os

os.makedirs("data/clean", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("sql", exist_ok=True)
os.makedirs("state", exist_ok=True)

# Load Raw Data
customers = pd.read_csv("data/raw/customers.csv")
products = pd.read_csv("data/raw/products.csv")
orders = pd.read_csv("data/raw/orders.csv")

# Clean Customers
customers['city'] = customers['city'].astype(str).str.strip().str.title()
customers['gender'] = customers['gender'].fillna('unknown').astype(str).str.lower()
valid_genders = {'male': 'male', 'female': 'female'}
customers['gender'] = customers['gender'].map(lambda x: valid_genders.get(x, 'unknown'))
customers.loc[(customers['age'] < 10) | (customers['age'] > 100), 'age'] = np.nan
city_medians = customers.groupby('city')['age'].transform('median')
customers['age'] = customers['age'].fillna(city_medians).fillna(customers['age'].median())

# Clean Orders
orders['order_ts'] = pd.to_datetime(orders['order_ts'])
orders = orders.drop_duplicates()
orders = orders.sort_values('order_ts').groupby('order_id').last().reset_index()
orders['order_amount'] = pd.to_numeric(orders['order_amount'], errors='coerce')

orders = orders.merge(products[['product_id', 'price_inr']], on='product_id', how='left')
discount = orders['discount_pct'].fillna(0) / 100.0
calc_amount = (orders['price_inr'] * (1 - discount)).round(2)
orders['order_amount'] = orders['order_amount'].fillna(calc_amount)

completed_mask = orders['status'] == 'completed'
median_del = orders.loc[completed_mask, 'delivery_minutes'].median()
orders.loc[completed_mask & (orders['delivery_minutes'] < 0), 'delivery_minutes'] = median_del
orders.loc[completed_mask, 'delivery_minutes'] = orders.loc[completed_mask, 'delivery_minutes'].fillna(median_del)

# Save Clean CSVs & SQLite DB
customers.to_csv("data/clean/customers.csv", index=False)
products.to_csv("data/clean/products.csv", index=False)
orders.drop(columns=['price_inr'], errors='ignore').to_csv("data/clean/orders.csv", index=False)

conn = sqlite3.connect("data/instamart.db")
customers.to_sql("customers", conn, if_exists="replace", index=False)
products.to_sql("products", conn, if_exists="replace", index=False)
orders.drop(columns=['price_inr'], errors='ignore').to_sql("orders", conn, if_exists="replace", index=False)
conn.close()

print("Data Cleaning & SQLite DB creation completed!")