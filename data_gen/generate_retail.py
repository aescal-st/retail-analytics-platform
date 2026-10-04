#Generate syntheic retails CSV for bronze s3 layer

import csv
import random
from datetime import date,timedelta
from pathlib import Path

random.seed(42)
OUT= Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

FIRST = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda","David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah"]
LAST = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas"]
CITIES = [("New York","NY"),("Los Angeles","CA"),("Chicago","IL"),("Houston","TX"),("Phoenix","AZ"),("Philadelphia","PA"),("San Antonio","TX"),("San Diego","CA"),("Dallas","TX"),("Austin","TX"),("Seattle","WA"),("Denver","CO")]
CATS = {
    "Electronics": [("Wireless Headphones",89.99),("Smart Watch",199.99),("Bluetooth Speaker",49.99),("USB-C Hub",39.99),("Mechanical Keyboard",129.99)],
    "Clothing": [("Denim Jacket",79.99),("Running Shoes",119.99),("Cotton T-Shirt",24.99),("Wool Sweater",69.99),("Athletic Shorts",34.99)],
    "Home": [("Ceramic Vase",29.99),("Throw Pillow",19.99),("Desk Lamp",44.99),("Cotton Duvet",89.99),("Wall Clock",34.99)],
    "Sports": [("Yoga Mat",29.99),("Dumbbell Set",79.99),("Tennis Racket",99.99),("Water Bottle",19.99),("Resistance Bands",24.99)],
    "Books": [("Data Engineering Handbook",49.99),("Mystery Novel",14.99),("Cookbook",29.99),("Sci-Fi Trilogy",39.99),("Biography",24.99)],
    "Toys": [("Building Blocks",39.99),("Board Game",29.99),("RC Car",59.99),("Puzzle 1000pc",19.99),("Dollhouse",79.99)],
}

with open(OUT / "customers.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["customer_id","first_name","last_name","email","city","state","signup_date"])
    for i in range(1, 1001):
        fn, ln = random.choice(FIRST), random.choice(LAST)
        city, state = random.choice(CITIES)
        w.writerow([i, fn, ln, f"{fn.lower()}.{ln.lower()}{i}@example.com", city, state,
                    (date(2024,1,1) + timedelta(days=random.randint(0,600))).isoformat()])

products =[]
pid =1
with open(OUT /"products.csv", "w", newline ="") as f:
    w=csv.writer(f)
    w.writerow(["product_id","product_name","category","unit_price"])
    for cat,items in CATS.items():
        for name,price in items:
            p = round(price * random.uniform(0.9, 1.1), 2)
            w.writerow([pid, name, cat, p])
            products.append((pid, p))
            pid += 1

oid = 1
today = date(2026, 10, 3)
with open(OUT / "orders.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["order_id","customer_id","product_id","quantity","unit_price","order_date","status"])
    for d in range(90):
        day = today - timedelta(days=89-d)
        n = int(random.gauss(160, 25) * (1.4 if day.weekday() in (5, 6) else 1.0))
        for _ in range(max(n, 50)):
            cid = random.randint(1, 1000)
            prod_id, price = random.choice(products)
            status = random.choices(["completed","completed","completed","cancelled","refunded"], k=1)[0]
            w.writerow([oid, cid, prod_id, random.randint(1,3), price, day.isoformat(), status])
            oid += 1

print(f"customers=1000 products={len(products)} orders={oid-1}")