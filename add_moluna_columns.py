
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("""
            ALTER TABLE bestellungen
            ADD COLUMN IF NOT EXISTS moluna_status VARCHAR(50),
            ADD COLUMN IF NOT EXISTS moluna_order_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS trackingnummer VARCHAR(100),
            ADD COLUMN IF NOT EXISTS logistiker VARCHAR(100),
            ADD COLUMN IF NOT EXISTS paketart VARCHAR(100),
            ADD COLUMN IF NOT EXISTS eans VARCHAR(500);
        """))

        db.session.commit()
        print("✅ Alle Spalten wurden hinzugefügt!")

    except Exception as e:
        print("⚠️ Fehler:", e)
