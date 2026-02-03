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

# ---------- SETUP ----------
load_dotenv()  # .env nur lokal laden

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            "beschreibung": res.get("text_text") or "",
            "bilder": [f"{BASE_URL}/image/{ean}"],
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


# ---------- SENDGRID KONFIGURATION ----------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

def send_email(subject, body, recipient=EMAIL_SENDER):
    if not SENDGRID_API_KEY or not EMAIL_SENDER:
        raise ValueError("SENDGRID_API_KEY oder EMAIL_SENDER ist nicht gesetzt!")
    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"E-Mail erfolgreich gesendet! Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail: {e}")
        raise RuntimeError(f"Fehler beim Senden der E-Mail: {e}")

# ---------- LOGIN / REGISTRIERUNG ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        email = request.form.get("email")
        password = request.form.get("password")

        if action == "register":
            if not email or not password:
                flash("Bitte alle Felder ausfüllen.", "error")
                return redirect(url_for("login"))
            if User.query.filter_by(email=email).first():
                flash("Diese E-Mail ist bereits registriert.", "error")
                return redirect(url_for("login"))
            hashed = generate_password_hash(password)
            db.session.add(User(email=email, password=hashed))
            db.session.commit()
            flash("Registrierung erfolgreich! Bitte melde dich an.", "success")
            return redirect(url_for("login"))

        elif action == "login":
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password, password):
                flash("Falsche E-Mail oder Passwort.", "error")
                return redirect(url_for("login"))
            session["user_id"] = user.id
            session["user_email"] = user.email
            flash("Erfolgreich eingeloggt!", "success")
            return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Du wurdest ausgeloggt.", "success")
    return redirect(url_for("login"))

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

# ---------- RESTLICHE ROUTES ----------

@app.route('/navbar')
def navbar():
    return render_template('navbar.html', user_email=session.get("user_email"))

@app.route('/team')
def team():
    return render_template('Team.html', user_email=session.get("user_email"))

@app.route('/vision')
def vision():
    return render_template('vision.html', user_email=session.get("user_email"))

@app.route('/presse')
def presse():
    return render_template('presse.html', user_email=session.get("user_email"))

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
        return redirect(url_for('bestelldanke'))

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


# ---------- BESTELLUNGEN SQLITE ----------
import sqlite3

basedir = os.path.abspath(os.path.dirname(__file__))
BESTELL_DB = os.path.join(basedir, "bestellungen.db")

def init_bestell_db():
    conn = sqlite3.connect(BESTELL_DB)
    cur = conn.cursor()

    # -------------------------
    # Hauptbestellung
    # -------------------------
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

    # -------------------------
    # Positionen
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestell_positionen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        ean TEXT,
        bezeichnung TEXT,
        menge INTEGER,
        ek_netto REAL,
        vk_brutto REAL,
        referenz TEXT
    )
    """)

    # -------------------------
    # Zusatzoptionen
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestell_zusatz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bestell_id INTEGER,
        typ TEXT,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

init_bestell_db()


@app.route("/bestellung", methods=["POST"])
def neue_bestellung():
    data = request.get_json()

    try:
        conn = sqlite3.connect(BESTELL_DB)
        cur = conn.cursor()

        # -------------------------
        # Bestellung speichern
        # -------------------------
        cur.execute("""
        INSERT INTO bestellungen (
            mol_kunde_id, rechnungsadresse_id, mol_zahlart_id,
            bestelldatum, bestellreferenz, seite, bestellfreigabe,
            mol_verkaufskanal_id,

            liefer_anrede, liefer_vorname, liefer_nachname,
            liefer_zusatz, liefer_strasse, liefer_hausnummer,
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

            data.get("lieferadresse", {}).get("anrede"),
            data.get("lieferadresse", {}).get("vorname"),
            data.get("lieferadresse", {}).get("nachname"),
            data.get("lieferadresse", {}).get("zusatz"),
            data.get("lieferadresse", {}).get("strasse"),
            data.get("lieferadresse", {}).get("hausnummer"),
            data.get("lieferadresse", {}).get("adresszeile_1"),
            data.get("lieferadresse", {}).get("adresszeile_2"),
            data.get("lieferadresse", {}).get("adresszeile_3"),
            data.get("lieferadresse", {}).get("plz"),
            data.get("lieferadresse", {}).get("ort"),
            data.get("lieferadresse", {}).get("land"),
            data.get("lieferadresse", {}).get("land_iso"),
            data.get("lieferadresse", {}).get("tel"),

            data.get("versand_einstellung_id"),
            data.get("collectkey")
        ))

        bestell_id = cur.lastrowid

        # -------------------------
        # Positionen speichern
        # -------------------------
        for pos in data.get("auftrag_position", []):
            cur.execute("""
            INSERT INTO bestell_positionen
            (bestell_id, ean, bezeichnung, menge, ek_netto, vk_brutto, referenz)
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

        # -------------------------
        # Zusatzdaten speichern
        # -------------------------
        for zusatz in data.get("auftrag_zusatz", []):
            cur.execute("""
            INSERT INTO bestell_zusatz
            (bestell_id, typ, value)
            VALUES (?,?,?)
            """, (
                bestell_id,
                zusatz.get("typ"),
                zusatz.get("value")
            ))

        conn.commit()
        conn.close()

        return {"success": True, "bestellId": bestell_id}

    except Exception as e:
        logger.exception("Bestellung speichern fehlgeschlagen")
        return {"success": False, "error": str(e)}, 500


@app.route("/bestellungen")
def alle_bestellungen():
    conn = sqlite3.connect(BESTELL_DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM bestellungen")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)

