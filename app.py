from flask import Flask, render_template, request, redirect, flash, abort, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import logging
import requests
import sqlite3
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ---------- SETUP ----------
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

# ---------- SQLALCHEMY USER DB ----------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()

# ---------- SQLITE BESTELLUNGEN DB ----------

basedir = os.path.abspath(os.path.dirname(__file__))
BESTELL_DB = os.path.join(basedir, "bestellungen.db")


def init_bestell_db():
    conn = sqlite3.connect(BESTELL_DB)
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
        referenz TEXT
    )
    """)

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

# ---------- PRODUKT JSON LADEN ----------

json_path = os.path.join(basedir, 'produkte.json')

if os.path.exists(json_path):
    with open(json_path, encoding='utf-8') as f:
        produkte = json.load(f)
else:
    produkte = []

# ---------- BUCHBUTLER API ----------

BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")
BASE_URL = "https://api.buchbutler.de"


def check_auth():
    return BUCHBUTLER_USER and BUCHBUTLER_PASSWORD


def to_float(value):
    try:
        return float(str(value).replace(",", "."))
    except:
        return 0.0


def to_int(value):
    try:
        return int(value)
    except:
        return 0


def attr(attrs, key):
    return (attrs.get(key) or {}).get("Wert", "")


def buchbutler_request(endpoint, ean):
    url = f"{BASE_URL}/{endpoint}/"

    params = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "ean": ean
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("response")


# ---------- CONTENT API ----------

def lade_produkt_von_api(ean):
    res = buchbutler_request("CONTENT", ean)
    if not res:
        return None

    attrs = res.get("Artikelattribute") or {}

    return {
        "name": res.get("bezeichnung"),
        "autor": attr(attrs, "Autor"),
        "preis": to_float(res.get("vk_brutto")),
        "beschreibung": res.get("text_text") or "",
        "bilder": [f"{BASE_URL}/image/{ean}"],
    }


# ---------- MOVEMENT API ----------

def lade_bestand_von_api(ean):
    res = buchbutler_request("MOVEMENT", ean)
    if isinstance(res, list) and res:
        res = res[0]

    if not res:
        return None

    return {
        "bestand": to_int(res.get("Bestand")),
        "preis": to_float(res.get("Preis")),
        "handling_zeit": res.get("Handling_Zeit_in_Werktagen")
    }


# ---------- SENDGRID ----------

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")


def send_email(subject, body, recipient=EMAIL_SENDER):
    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body
    )

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)


# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        action = request.form.get("action")
        email = request.form.get("email")
        password = request.form.get("password")

        if action == "register":
            if User.query.filter_by(email=email).first():
                flash("E-Mail existiert", "error")
                return redirect(url_for("login"))

            hashed = generate_password_hash(password)
            db.session.add(User(email=email, password=hashed))
            db.session.commit()

        elif action == "login":
            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password, password):
                flash("Login fehlgeschlagen", "error")
                return redirect(url_for("login"))

            session["user_email"] = user.email
            return redirect(url_for("index"))

    return render_template("login.html")


# ---------- SHOP ----------

@app.route('/')
def index():
    return render_template("index.html", produkte=produkte)


@app.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)

    if not produkt:
        abort(404)

    if produkt.get("ean"):
        api_data = lade_produkt_von_api(produkt["ean"])
        if api_data:
            produkt.update(api_data)

        movement = lade_bestand_von_api(produkt["ean"])
        if movement:
            produkt.update(movement)

    return render_template("produkt.html", produkt=produkt)


# ---------- BESTELLUNG SPEICHERN ----------

@app.route("/bestellung", methods=["POST"])
def neue_bestellung():

    data = request.get_json()

    conn = sqlite3.connect(BESTELL_DB)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO bestellungen (
        mol_kunde_id, bestellreferenz
    )
    VALUES (?,?)
    """, (
        data.get("mol_kunde_id"),
        data.get("bestellreferenz")
    ))

    bestell_id = cur.lastrowid

    for pos in data.get("auftrag_position", []):
        cur.execute("""
        INSERT INTO bestell_positionen
        (bestell_id, ean, menge)
        VALUES (?,?,?)
        """, (
            bestell_id,
            pos.get("ean"),
            pos.get("menge")
        ))

    conn.commit()
    conn.close()

    return {"success": True}


# ---------- BESTELLUNGEN AUSLESEN ----------

@app.route("/bestellungen")
def alle_bestellungen():

    conn = sqlite3.connect(BESTELL_DB)
    cur = conn.cursor()

    cur.execute("SELECT * FROM bestellungen")
    rows = cur.fetchall()

    conn.close()

    return jsonify(rows)


# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
