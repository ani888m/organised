import csv
import json

products = []

with open("moluna.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile, delimiter=";")
    for row in reader:
        products.append({
            "ean": row["EAN"],
            "stock": int(row["Bestand"]),
            "price": float(row["Preis"].replace(",", ".")),
            "vat": float(row["Umsatzsteuer_Deutschland"]),
            "delivery_days": int(row["Handling_Zeit"]),
            "fulfillment": int(row["Erfuellungsrate"])
        })

with open("products.json", "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("✅ Moluna Daten importiert")
