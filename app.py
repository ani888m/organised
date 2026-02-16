from flask import Flask, render_template, request, redirect, flash, abort, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps
from moluna_mapper import build_moluna_payload
from moluna_client import send_order_to_moluna


# -------------------------------------------------
# SETUP
# -------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
secret = os.getenv("FLASK_SECRET_KEY")
if not secret:
    raise RuntimeError("FLASK_SECRET_KEY nicht gesetzt!")
app.secret_key = secret


database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

logger = logging.getLogger(__name__)

BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")
BASE_URL = "https://api.buchbutler.de"


# -------------------------------------------------
# HELPER
# -------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_email"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def check_auth():
    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        logger.error("Buchbutler Zugangsdaten fehlen")
        return False
    return True


def to_float(value):
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def to_int(value):
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
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
    data = response.json()

    if not data or "response" not in data:
        return None

    return data["response"]


# -------------------------------------------------
# API CALLS
# -------------------------------------------------

def lade_produkt_von_api(ean):
    if not check_auth():
        return None

    try:
        res = buchbutler_request("CONTENT", ean)
        if not res:
            return None

        attrs = res.get("Artikelattribute") or {}

        return {
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
            "extra": attrs
        }

    except Exception:
        logger.exception("Fehler CONTENT API")
        return None


def lade_bestand_von_api(ean):
    if not check_auth():
        return None

    try:
        res = buchbutler_request("MOVEMENT", ean)
        if not res:
            return None

        if isinstance(res, list):
            if not res:
                return None
            res = res[0]

        return {
            "bestand": to_int(res.get("Bestand")),
            "preis": to_float(res.get("Preis")),
            "erfuellungsrate": res.get("Erfuellungsrate"),
            "handling_zeit": res.get("Handling_Zeit_in_Werktagen")
        }

    except Exception:
        logger.exception("Fehler MOVEMENT API")
        return None


# -------------------------------------------------
# MODELS
# -------------------------------------------------

class Bestellung(db.Model):
    __tablename__ = "bestellungen"

    id = db.Column(db.Integer, primary_key=True)
    bestelldatum = db.Column(db.String(50))
    bestellreferenz = db.Column(db.String(100))
    status = db.Column(db.String(50), default="neu")
    trackingnummer = db.Column(db.String(100))
    versanddienstleister = db.Column(db.String(100))
    versanddatum = db.Column(db.String(50))

    positionen = db.relationship("BestellPosition", backref="bestellung", cascade="all, delete-orphan")


class BestellPosition(db.Model):
    __tablename__ = "bestell_positionen"

    id = db.Column(db.Integer, primary_key=True)
    bestell_id = db.Column(db.Integer, db.ForeignKey("bestellungen.id"), nullable=False)
    ean = db.Column(db.String(20))
    bezeichnung = db.Column(db.String(500))
    menge = db.Column(db.Integer)
    ek_netto = db.Column(db.Float)
    vk_brutto = db.Column(db.Float)


with app.app_context():
    db.create_all()


# -------------------------------------------------
# BESTELLUNG
# -------------------------------------------------

@app.route("/bestellung", methods=["POST"])
def neue_bestellung():
    try:
        data = request.get_json() or {}

        bestellung = Bestellung(
            bestelldatum=data.get("bestelldatum"),
            bestellreferenz=data.get("bestellreferenz"),
        )

        db.session.add(bestellung)
        db.session.flush()

        for pos in data.get("auftrag_position", []):

            try:
                menge = int(pos.get("menge", 0))
            except:
                menge = 0

            try:
                ek_netto = float(pos.get("ek_netto", 0))
            except:
                ek_netto = 0.0

            try:
                vk_brutto = float(pos.get("vk_brutto", 0))
            except:
                vk_brutto = 0.0

            db.session.add(BestellPosition(
                bestell_id=bestellung.id,
                ean=pos.get("ean"),
                bezeichnung=pos.get("pos_bezeichnung"),
                menge=menge,
                ek_netto=ek_netto,
                vk_brutto=vk_brutto,
            ))

        db.session.commit()
        return jsonify({"success": True, "bestellId": bestellung.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------
# PRODUKTE
# -------------------------------------------------


# Produkte einmal beim Start laden
with open("produkte.json", encoding="utf-8") as f:
    produkte = json.load(f)


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

    original = next((p for p in produkte if p['id'] == produkt_id), None)

    if not original:
        abort(404)

    produkt = original.copy()

    if produkt.get("ean"):
        api_data = lade_produkt_von_api(produkt["ean"])
        if api_data:
            produkt.update(api_data)

        movement = lade_bestand_von_api(produkt["ean"])
        if movement:
            produkt.update(movement)

    produkt.setdefault("bestand", "n/a")
    produkt.setdefault("preis", 0)

    return render_template("produkt.html", produkt=produkt)


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
        {'title': 'Reife Blessuren | Danilo Lučić', 'price': 23.90, 'quantity': 1, 'image': '/static/images/image/reifeblessuren.jpg'}
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





# -------------------------------------------------
# START
# -------------------------------------------------

if __name__ == "__main__":
    app.run()
