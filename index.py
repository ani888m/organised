from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_PATH = "bestellungen.db"

# --- Tabelle erstellen, falls sie noch nicht existiert ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestellungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mol_kunde_id INTEGER,
        rechnungsadresse_id INTEGER,
        mol_zahlart_id INTEGER,
        bestelldatum TEXT,
        bestellreferenz TEXT,
        seite TEXT,
        bestellfreigabe INTEGER,
        mol_verkaufskanal_id INTEGER,
        liefer_anrede TEXT,
        liefer_vorname TEXT,
        liefer_nachname TEXT,
        liefer_zusatz TEXT,
        liefer_strasse TEXT,
        liefer_hausnummer TEXT,
        liefer_adresszeile1 TEXT,
        liefer_adresszeile2 TEXT,
        liefer_adresszeile3 TEXT,
        liefer_plz TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Endpunkt für neue Bestellung ---
@app.route("/bestellung", methods=["POST"])
def neue_bestellung():
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO bestellungen
        (mol_kunde_id, rechnungsadresse_id, mol_zahlart_id, bestelldatum, bestellreferenz, seite, bestellfreigabe, mol_verkaufskanal_id,
         liefer_anrede, liefer_vorname, liefer_nachname, liefer_zusatz, liefer_strasse, liefer_hausnummer, liefer_adresszeile1,
         liefer_adresszeile2, liefer_adresszeile3, liefer_plz)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["mol_kunde_id"], data["rechnungsadresse_id"], data["mol_zahlart_id"], data["bestelldatum"], data["bestellreferenz"],
            data["seite"], data["bestellfreigabe"], data["mol_verkaufskanal_id"],
            data["lieferadresse"]["anrede"], data["lieferadresse"]["vorname"], data["lieferadresse"]["nachname"], data["lieferadresse"]["zusatz"],
            data["lieferadresse"]["strasse"], data["lieferadresse"]["hausnummer"], data["lieferadresse"]["adresszeile_1"],
            data["lieferadresse"]["adresszeile_2"], data["lieferadresse"]["adresszeile_3"], data["lieferadresse"]["plz"]
        ))
        conn.commit()
        bestell_id = cur.lastrowid
        conn.close()
        return jsonify({"success": True, "bestellId": bestell_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route("/bestellungen", methods=["GET"])
def alle_bestellungen():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM bestellungen")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)
