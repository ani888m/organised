

from flask import Flask, render_template, request, redirect, flash, abort, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import logging
import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import secrets
from datetime import datetime
from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
import base64
from moluna_mapper import build_moluna_payload
from moluna_client import send_order_to_moluna

# ---------- SETUP ----------
load_dotenv()  # .env nur lokal laden

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG)

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

# Datenbank Setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- DATENBANKMODELLE ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

# ---------- PRODUKT DATEN LADEN ----------
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')

if os.path.exists(json_path):
    with open(json_path, encoding='utf-8') as f:
        produkte = json.load(f)
else:
    produkte = []  # Falls Datei fehlt

# ---------- BUCHBUTLER API ZUGANG ----------


logger = logging.getLogger(__name__)

BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")

BASE_URL = "https://api.buchbutler.de"

# Alias für Moluna Order Schnittstelle
MOLUNA_USER = BUCHBUTLER_USER
MOLUNA_PASS = BUCHBUTLER_PASSWORD

TEST_MODE = True

# -----------------------------
# Helper Funktionen
# -----------------------------

def check_auth():
    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        logger.error("Buchbutler Zugangsdaten fehlen")
        return False
    return True


def to_float(value):
    """Konvertiert API Preis sicher"""
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def to_int(value):
    """Konvertiert Zahlen sicher"""
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def attr(attrs, key):
    """Greift sicher auf Artikelattribute zu"""
    return (attrs.get(key) or {}).get("Wert", "")


def buchbutler_request(endpoint, ean):
    """Allgemeine Request Funktion"""
    url = f"{BASE_URL}/{endpoint}/"

    params = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "ean": ean
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if not data or "response" not in data:
        return None

    return data["response"]


# -----------------------------
# CONTENT API
# -----------------------------

def lade_produkt_von_api(ean):
    """Lädt Produktdaten von CONTENT API"""

    if not check_auth():
        return None

    try:
        res = buchbutler_request("CONTENT", ean)

        if not res:
            return None

        attrs = res.get("Artikelattribute") or {}

        produkt = {
            "id": to_int(res.get("pim_artikel_id")),
            "name": res.get("bezeichnung"),
            "autor": attr(attrs, "Autor"),
            "preis": to_float(res.get("vk_brutto")),
           
            "isbn": attr(attrs, "ISBN_13"),
            "seiten": attr(attrs, "Seiten"),
            "format": attr(attrs, "Buchtyp"),
            "sprache": attr(attrs, "Sprache"),
            "verlag": attr(attrs, "Verlag"),
            "erscheinungsjahr": attr(attrs, "Erscheinungsjahr"),
            "erscheinungsdatum": attr(attrs, "Erscheinungsdatum"),
            "alter_von": attr(attrs, "Altersempfehlung_von"),
            "alter_bis": attr(attrs, "Altersempfehlung_bis"),
            "lesealter": attr(attrs, "Lesealter"),
            "gewicht": attr(attrs, "Gewicht"),
            "laenge": attr(attrs, "Laenge"),
            "breite": attr(attrs, "Breite"),
            "hoehe": attr(attrs, "Hoehe"),
            "extra": attrs
        }

        return produkt

    except Exception:
        logger.exception("Fehler beim Laden von CONTENT API")
        return None


# -----------------------------
# MOVEMENT API
# -----------------------------

def lade_bestand_von_api(ean):
    """Lädt Bestand / Preis / Lieferdaten"""

    if not check_auth():
        return None

    try:
        res = buchbutler_request("MOVEMENT", ean)

        if not res:
            return None

        # 🔥 FIX — falls Liste zurückkommt
        if isinstance(res, list):
            if len(res) == 0:
                return None
            res = res[0]

        return {
            "bestand": to_int(res.get("Bestand")),
            "preis": to_float(res.get("Preis")),
            "erfuellungsrate": res.get("Erfuellungsrate"),
            "handling_zeit": res.get("Handling_Zeit_in_Werktagen")

        }


    except Exception:
        logger.exception("Fehler beim Laden von MOVEMENT API")
        return None




# ---------- BESTELLUNGEN SQLITE ----------
import sqlite3
import os
from flask import request, jsonify

basedir = os.path.abspath(os.path.dirname(__file__))
BESTELL_DB = os.path.join(basedir, "bestellungen.db")


# -------------------------------------------------
# DB Verbindung Helper
# -------------------------------------------------
def get_db():
    conn = sqlite3.connect(BESTELL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# -------------------------------------------------
# DB Initialisierung
# -------------------------------------------------
def init_bestell_db():
    conn = get_db()
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
        email TEXT,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestell_zusatz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        typ TEXT,
        value TEXT,
        FOREIGN KEY(bestell_id) REFERENCES bestellungen(id) ON DELETE CASCADE
    )
    """)

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


init_bestell_db()


# -------------------------------------------------
# Bestellung speichern
# -------------------------------------------------
@app.route("/bestellung", methods=["POST"])
def neue_bestellung():

    data = request.get_json() or {}
    liefer = data.get("lieferadresse", {})

    conn = get_db()
    cur = conn.cursor()

    try:
        # -------------------------
        # Bestellung speichern
        # -------------------------
        cur.execute("""
        INSERT INTO bestellungen (
            mol_kunde_id, rechnungsadresse_id, mol_zahlart_id,
            bestelldatum, bestellreferenz, seite,
            bestellfreigabe, mol_verkaufskanal_id,

            liefer_anrede, liefer_vorname, liefer_nachname, liefer_zusatz,
            liefer_strasse, liefer_hausnummer,
            liefer_adresszeile1, liefer_adresszeile2, liefer_adresszeile3,
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

        # -------------------------
        # Positionen speichern
        # -------------------------
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
                int(pos.get("menge", 0)),
                float(pos.get("ek_netto", 0)),
                float(pos.get("vk_brutto", 0)),
                pos.get("pos_referenz")
            ))



        conn.commit()

        # -------------------------
        # Mail + Storno
        # -------------------------
        email = data.get("email")

        if email:

            token = generate_cancel_token(bestell_id)
            cancel_link = f"https://deinedomain.de/storno/{token}"

            pdf_bytes = None
            if data.get("rechnungsdatei"):
                pdf_bytes = lade_rechnung(data["rechnungsdatei"])

            try:
                send_email(
                    subject="Ihre Bestellung",
                    body=f"""
Vielen Dank für Ihre Bestellung!

Bestellnummer: {bestell_id}

Stornieren Sie hier:
{cancel_link}
""",
                    recipient=email,
                    pdf_bytes=pdf_bytes
                )
            except Exception as e:
                logger.error(f"Bestellmail Fehler: {e}")

        return jsonify({
            "success": True,
            "bestellId": bestell_id
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        conn.close()


# -------------------------------------------------
# Alle Bestellungen (nur Kopf)
# -------------------------------------------------
@app.route("/bestellungen")
def alle_bestellungen():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bestellungen")
    rows = [dict(row) for row in cur.fetchall()]

    conn.close()
    return jsonify(rows)


# -------------------------------------------------
# Bestellung Detail inkl Positionen + Zusatz
# -------------------------------------------------
@app.route("/bestellung/<int:bestell_id>")
def bestellung_detail(bestell_id):

    conn = get_db()
    cur = conn.cursor()

    # Bestellung
    cur.execute("SELECT * FROM bestellungen WHERE id=?", (bestell_id,))
    bestellung = cur.fetchone()

    if not bestellung:
        return jsonify({"error": "Nicht gefunden"}), 404

    # Positionen
    cur.execute("""
        SELECT * FROM bestell_positionen
        WHERE bestell_id=?
    """, (bestell_id,))
    positionen = [dict(row) for row in cur.fetchall()]

    # Zusatz
    cur.execute("""
        SELECT * FROM bestell_zusatz
        WHERE bestell_id=?
    """, (bestell_id,))
    zusatz = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify({
        "bestellung": dict(bestellung),
        "positionen": positionen,
        "zusatz": zusatz
    })


# -------------------------------------------------
# Bestellung löschen
# -------------------------------------------------
@app.route("/bestellung/<int:bestell_id>", methods=["DELETE"])
def bestellung_loeschen(bestell_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM bestellungen WHERE id=?", (bestell_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# -------------------------------------------------
# Bestellung an Moluna sebden
# -------------------------------------------------

def lade_bestellung(bestell_id):

    conn = get_db()
    cur = conn.cursor()

    # Bestellung
    cur.execute("SELECT * FROM bestellungen WHERE id=?", (bestell_id,))
    bestellung = cur.fetchone()

    if not bestellung:
        conn.close()
        return None

    # Positionen
    cur.execute("""
        SELECT * FROM bestell_positionen
        WHERE bestell_id=?
    """, (bestell_id,))
    positionen = [dict(row) for row in cur.fetchall()]

    # Zusatz
    cur.execute("""
        SELECT * FROM bestell_zusatz
        WHERE bestell_id=?
    """, (bestell_id,))
    zusatz = [dict(row) for row in cur.fetchall()]

    conn.close()

    return {
        "bestellung": dict(bestellung),
        "positionen": positionen,
        "zusatz": zusatz
    }




def send_bestellung_an_moluna(bestell_id):

    order = lade_bestellung(bestell_id)

    if not order:
        raise Exception("Bestellung nicht gefunden")

    payload = build_moluna_payload(order, MOLUNA_USER, MOLUNA_PASS)

    # ---------- TEST MODE ----------
    if TEST_MODE:
        logger.info("TEST MODE – Bestellung wird NICHT gesendet")
        return payload

    response = send_order_to_moluna(payload)

    return response


# ----zum Testen -----


    
@app.route("/test_moluna/<int:bestell_id>")
def test_moluna(bestell_id):

    try:
        response = send_bestellung_an_moluna(bestell_id)

        return jsonify({
            "status": "ok",
            "moluna_response": str(response)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------- SENDGRID KONFIGURATION ----------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

def send_email(subject, body, recipient=None, pdf_bytes=None):

    if not recipient:
        recipient = EMAIL_SENDER

    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body
    )

    # 📄 PDF anhängen
    if pdf_bytes:
        encoded_file = base64.b64encode(pdf_bytes).decode()

        attachment = Attachment(
            FileContent(encoded_file),
            FileName("Rechnung.pdf"),
            FileType("application/pdf"),
            Disposition("attachment")
        )

        message.attachment = attachment

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info("E-Mail erfolgreich gesendet")
    except Exception as e:
        logger.error(f"E-Mail Fehler: {e}")
        raise


# ---------- PRODUKT-SEITEN ----------
@app.route('/')
def index():
    kategorienamen = [
        "Jacominus Gainsborough", "Mut oder Angst?!",
        "Klassiker", "Monstergeschichten", "Wichtige Fragen", "Weihnachten",
        "Kinder und Gefühle", "Dazugehören"
    ]
    kategorien = [(k, [p for p in produkte if p.get("kategorie") == k]) for k in kategorienamen]
    return render_template("index.html", kategorien=kategorien, user_email=session.get("user_email"))

@app.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)
    if not produkt:
        abort(404)

    # 1️⃣ CONTENT API Daten laden
    if produkt.get("ean"):
        api_produkt = lade_produkt_von_api(produkt["ean"])
        if api_produkt:
            produkt.update(api_produkt)

        movement = lade_bestand_von_api(produkt["ean"])
        if movement:
            produkt.update(movement)

    # 2️⃣ Default-Werte setzen
    produkt.setdefault("bestand", "n/a")
    produkt.setdefault("preis", 0)
    produkt.setdefault("handling_zeit", "n/a")
    produkt.setdefault("erfuellungsrate", "n/a")

    return render_template('produkt.html', produkt=produkt, user_email=session.get("user_email"))


# ------STORNO---------

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


def lade_rechnung(dateiname):
    url = f"https://api.buchbutler.de/RECHNUNG/{dateiname}"

    response = requests.get(url, auth=(BUCHBUTLER_USER, BUCHBUTLER_PASSWORD))

    if response.status_code == 200:
        return response.content  # PDF Bytes

    return None



# ---------- RESTLICHE ROUTES ----------

@app.route('/navbar')
def navbar():
    return render_template('navbar.html', user_email=session.get("user_email"))



@app.route('/kontakt')
def kontakt():
    return render_template('kontakt.html', user_email=session.get("user_email"))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        newsletter = request.form.get('newsletter')
        payment_method = request.form.get('payment-method')

        if not name or not email or not payment_method:
            flash("Bitte fülle alle Pflichtfelder aus.", "error")
            return redirect(url_for('checkout'))

        if newsletter:
            try:
                send_email(
                    subject='Neue Newsletter-Anmeldung (über Bestellung)',
                    body=f'{name} ({email}) hat sich beim Bestellvorgang für den Newsletter angemeldet.'
                )
            except Exception as e:
                logger.warning(f"Newsletter konnte nicht gesendet werden: {e}")

        flash("Zahlung erfolgreich (Simulation). Vielen Dank für deine Bestellung!", "success")
        return redirect(url_for('kontaktdanke'))

    return render_template('checkout.html', user_email=session.get("user_email"))




@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    if not name or not email or not message:
        flash("Bitte fülle alle Felder aus!", "error")
        return redirect('/kontakt')

    try:
        send_email(
            subject=f'Neue Nachricht von {name}',
            body=f"Von: {name} <{email}>\n\nNachricht:\n{message}"
        )

        flash("Danke! Deine Nachricht wurde gesendet.", "success")
        return redirect('/kontaktdanke')

    except Exception as e:
        flash(f"Fehler beim Senden der Nachricht: {e}", "error")
        return redirect('/kontakt')

@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email')
    if not email:
        flash('Bitte gib eine gültige E-Mail-Adresse ein.', 'error')
        return redirect('/')
    try:
        send_email(
            subject='Neue Newsletter-Anmeldung',
            body=f'Neue Newsletter-Anmeldung: {email}'
        )
        flash("Danke! Newsletter-Anmeldung erfolgreich.", "success")
        return redirect('/danke')
    except Exception as e:
        flash(f"Fehler beim Newsletter-Versand: {e}", 'error')
        return redirect('/')

@app.route('/danke')
def danke():
    return render_template('danke.html', user_email=session.get("user_email"))

@app.route('/kontaktdanke')
def kontaktdanke():
    return render_template('kontaktdanke.html', user_email=session.get("user_email"))

@app.route('/bestelldanke')
def bestelldanke():
    return render_template('bestelldanke.html', user_email=session.get("user_email"))

@app.route('/cart')
def cart():
    cart_items = [
        {'title': 'Reife Blessuren | Danilo Lučić', 'price': 23.90, 'quantity': 1}
    ]
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, user_email=session.get("user_email"))

@app.route('/rechtliches')
def rechtliches():
    return render_template('rechtliches.html', user_email=session.get("user_email"))

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html', user_email=session.get("user_email"))

@app.route('/impressum')
def impressum():
    return render_template('impressum.html', user_email=session.get("user_email"))

@app.route("/cron")
def cron():
    print("Cronjob wurde ausgelöst")
    return "OK"

# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
