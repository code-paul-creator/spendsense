"""
SpendSense - Synthetic Transaction Data Generator
==================================================
Simulates a year of UPI/bank transactions for one user at realistic scale,
with injected anomalies, so the pipeline has something real to detect.

This stands in for the INGEST step: in production this would instead be a
CSV exported from a bank/UPI app and uploaded to Cloud Storage.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

CATEGORIES = {
    "Food & Dining":     (80, 600),
    "Groceries":         (150, 2500),
    "Transport":         (30, 400),
    "Shopping":          (200, 5000),
    "Bills & Utilities": (300, 3500),
    "Entertainment":     (100, 1500),
    "Health":            (150, 4000),
    "Rent":              (8000, 8000),
    "Subscriptions":     (99, 999),
    "Transfers":         (100, 10000),
}

MERCHANTS = {
    "Food & Dining": ["Zomato", "Swiggy", "Cafe Coffee Day", "Local Tiffin", "Dominos"],
    "Groceries": ["BigBasket", "Blinkit", "DMart", "Local Kirana"],
    "Transport": ["Uber", "Ola", "Metro Card", "Petrol Pump"],
    "Shopping": ["Amazon", "Flipkart", "Myntra", "Local Store"],
    "Bills & Utilities": ["Electricity Board", "Jio Fiber", "Water Bill", "Gas Cylinder"],
    "Entertainment": ["Netflix", "BookMyShow", "Spotify"],
    "Health": ["Apollo Pharmacy", "Local Clinic", "PharmEasy"],
    "Rent": ["Landlord Transfer"],
    "Subscriptions": ["YouTube Premium", "Prime Video", "Cloud Storage Plan"],
    "Transfers": ["Friend UPI", "Family UPI", "Roommate Split"],
}

CAT_WEIGHTS = [18, 14, 12, 14, 10, 8, 6, 5, 5, 8]


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days),
                              seconds=random.randint(0, 86399))


def generate(num_rows=600_000, out_path="transactions.csv"):
    start = datetime(2025, 7, 1)
    end   = datetime(2026, 6, 30)
    rows  = []
    txn_id = 1

    while len(rows) < num_rows - 40:
        cat      = random.choices(list(CATEGORIES.keys()), weights=CAT_WEIGHTS)[0]
        low, high = CATEGORIES[cat]
        amount   = round(random.uniform(low, high), 2)
        merchant = random.choice(MERCHANTS[cat])
        dt       = random_date(start, end)
        rows.append([txn_id, dt.isoformat(), merchant, cat, amount])
        txn_id  += 1

    # Injected anomalies
    anomaly_cats = ["Shopping", "Transfers", "Entertainment", "Health"]
    for _ in range(40):
        cat      = random.choice(anomaly_cats)
        low, high = CATEGORIES[cat]
        amount   = round(high * random.uniform(5, 15), 2)
        merchant = random.choice(MERCHANTS[cat] + ["Unknown Merchant"])
        dt       = random_date(start, end)
        rows.append([txn_id, dt.isoformat(), merchant, cat, amount])
        txn_id  += 1

    random.shuffle(rows)

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["txn_id", "timestamp", "merchant", "category", "amount"])
        writer.writerows(rows)

    print(f"Generated {len(rows):,} transactions -> {out_path}")


if __name__ == "__main__":
    generate()
