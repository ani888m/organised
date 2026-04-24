# sync_buchbutler.py
import os
from app import app, db, lade_produkt_von_api, lade_bestand_von_api
from models import Produkt

with app.app_context():
    alle_produkte = Produkt.query.all()
    for produkt in alle_produkte:
        api = lade_produkt_von_api(produkt.ean)
        movement = lade_bestand_von_api(produkt.ean)

        if api:
            produkt.name = api.get("name")
            produkt.autor = api.get("autor")
        if movement:
            produkt.preis = movement.get("preis")

        db.session.add(produkt)

    db.session.commit()
    print("✅ Sync abgeschlossen")
