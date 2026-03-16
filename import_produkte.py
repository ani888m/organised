
import os
import json
from app import app, db, Produkt, json_path

with app.app_context():
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            produkte = json.load(f)

        for p in produkte:
            ean = p.get("ean")
            if not ean:
                continue

            existing = Produkt.query.filter_by(ean=ean).first()
            if existing:
                continue

            db.session.add(
                Produkt(
                    ean=ean,
                    name=p.get("name"),
                    autor=p.get("autor"),
                    preis=p.get("preis", 0),
                    json_data=p
                )
            )
        db.session.commit()
        print("✅ Produkte importiert")
    else:
        print("❌ JSON-Datei nicht gefunden")
