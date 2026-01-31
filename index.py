from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Verbindung zur Datenbank
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)

@app.route("/bestellung", methods=["POST"])
def neue_bestellung():
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bestellungen 
                (mol_kunde_id, rechnungsadresse_id, mol_zahlart_id, bestelldatum, bestellreferenz, seite, bestellfreigabe, mol_verkaufskanal_id,
                liefer_anrede, liefer_vorname, liefer_nachname, liefer_zusatz, liefer_strasse, liefer_hausnummer, liefer_adresszeile1,
                liefer_adresszeile2, liefer_adresszeile3, liefer_plz)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                data["mol_kunde_id"], data["rechnungsadresse_id"], data["mol_zahlart_id"], data["bestelldatum"], data["bestellreferenz"],
                data["seite"], data["bestellfreigabe"], data["mol_verkaufskanal_id"],
                data["lieferadresse"]["anrede"], data["lieferadresse"]["vorname"], data["lieferadresse"]["nachname"], data["lieferadresse"]["zusatz"],
                data["lieferadresse"]["strasse"], data["lieferadresse"]["hausnummer"], data["lieferadresse"]["adresszeile_1"],
                data["lieferadresse"]["adresszeile_2"], data["lieferadresse"]["adresszeile_3"], data["lieferadresse"]["plz"]
            ))
            bestell_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({"success": True, "bestellId": bestell_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
