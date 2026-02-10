import sqlite3
import os
from datetime import datetime
import secrets
from flask import current_app as app
from buchbutler import lade_rechnung

basedir = os.path.abspath(os.path.dirname(__file__))
BESTELL_DB = os.path.join(basedir, "../bestellungen.db")


# --------------------------------
# DB Verbindung Helper
# --------------------------------
def get_db():
    conn = sqlite3.connect(BESTELL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --------------------------------
# DB Initialisierung
# --------------------------------
def init_bestell_db():
    conn = get_db()
    cur = conn.cursor()

    # Bestellungen
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
        liefer_plz TEXT,
        liefer_ort TEXT,
        liefer_land TEXT,
        liefer_land_iso TEXT,
        liefer_tel TEXT,
        versand_einstellung_id INTEGER,
        collectkey TEXT
    )
    """)

    # Positionen
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestell_positionen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        ean TEXT,
        bezeichnung TEXT,
        menge INTEGER,
        ek_netto REAL,
        vk_brutto REAL,
        referenz TEXT,
        FOREIGN KEY(bestell_id) REFERENCES bestellungen(id) ON DELETE CASCADE
    )
    """)

    # Zusatzinformationen
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestell_zusatz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        typ TEXT,
        value TEXT,
        FOREIGN KEY(bestell_id) REFERENCES bestellungen(id) ON DELETE CASCADE
    )
    """)

    # Stornotoken
    cur.execute("""
    CREATE TABLE IF NOT EXISTS storno_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        token TEXT,
        created TEXT,
        FOREIGN KEY(bestell_id) REFERENCES bestellungen(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


# --------------------------------
# Neue Bestellung speichern
# --------------------------------
def save_order(data):
    liefer = data.get("lieferadresse", {})
    conn = get_db()
    cur = conn.cursor()

    try:
        # Bestellung speichern
        cur.execute("""
        INSERT INTO bestellungen (
            mol_kunde_id, rechnungsadresse_id, mol_zahlart_id,
            bestelldatum, bestellreferenz, seite,
            bestellfreigabe, mol_verkaufskanal_id,
            liefer_anrede, liefer_vorname, liefer_nachname, liefer_zusatz,
            liefer_strasse, liefer_hausnummer, liefer_adresszeile1, liefer_adresszeile2, liefer_adresszeile3,
            liefer_plz, liefer_ort, liefer_land, liefer_land_iso, liefer_tel,
            versand_einstellung_id, collectkey
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("mol_kunde_id"),
            data.get("rechnungsadresse_id"),
            data.get("mol_zahlart_id"),
            data.get("bestelldatum"),
            data.get("bestellreferenz"),
            data.get("seite"),
            data.get("bestellfreigabe"),
            data.get("mol_verkaufskanal_id"),
            liefer.get("anrede"),
            liefer.get("vorname"),
            liefer.get("nachname"),
            liefer.get("zusatz"),
            liefer.get("strasse"),
            liefer.get("hausnummer"),
            liefer.get("adresszeile_1"),
            liefer.get("adresszeile_2"),
            liefer.get("adresszeile_3"),
            liefer.get("plz"),
            liefer.get("ort"),
            liefer.get("land"),
            liefer.get("land_iso"),
            liefer.get("tel"),
            data.get("versand_einstellung_id"),
            data.get("collectkey")
        ))

        bestell_id = cur.lastrowid

        # Positionen speichern
        for pos in data.get("auftrag_position", []):
            cur.execute("""
            INSERT INTO bestell_positionen (
                bestell_id, ean, bezeichnung,
                menge, ek_netto, vk_brutto, referenz
            )
            VALUES (?,?,?,?,?,?,?)
            """, (
                bestell_id,
                pos.get("ean"),
                pos.get("pos_bezeichnung"),
                pos.get("menge"),
                pos.get("ek_netto"),
                pos.get("vk_brutto"),
                pos.get("pos_referenz")
            ))

        conn.commit()
        return bestell_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


# --------------------------------
# Stornotoken generieren
# --------------------------------
def generate_cancel_token(bestell_id):
    token = secrets.token_urlsafe(32)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO storno_tokens (bestell_id, token, created)
        VALUES (?, ?, ?)
    """, (bestell_id, token, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return token


# --------------------------------
# Bestellungen abrufen
# --------------------------------
def get_order(bestell_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bestellungen WHERE id=?", (bestell_id,))
    order = cur.fetchone()

    cur.execute("SELECT * FROM bestell_positionen WHERE bestell_id=?", (bestell_id,))
    positions = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT * FROM bestell_zusatz WHERE bestell_id=?", (bestell_id,))
    zusatz = [dict(row) for row in cur.fetchall()]

    conn.close()

    if order:
        return {
            "bestellung": dict(order),
            "positionen": positions,
            "zusatz": zusatz
        }
    return None


# --------------------------------
# Alle Bestellungen
# --------------------------------
def get_all_orders():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bestellungen")
    orders = [dict(row) for row in cur.fetchall()]
    conn.close()
    return orders


# --------------------------------
# Bestellung löschen
# --------------------------------
def delete_order(bestell_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bestellungen WHERE id=?", (bestell_id,))
    conn.commit()
    conn.close()
    return True


# Initialisierung direkt beim Import
init_bestell_db()
