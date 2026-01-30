from flask import Flask, render_template, request, redirect, flash, abort, session, url_for
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

BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")


# ⭐ NEU → Lager & Verfügbarkeitsdaten laden
def lade_lager_von_api(ean):

    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        return {}

    url = "https://api.buchbutler.de/AVAILABILITY/"
    params = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "ean": ean
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        res = data.get("response")
        if not res:
            return {}

        return res[0]  # API liefert Array

    except Exception as e:
        logger.error(f"Lager API Fehler: {e}")
        return {}



# ---------- PRODUKT LADEN ----------
def lade_produkt_von_api(ean):

    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        logger.error("Buchbutler Zugangsdaten fehlen")
        return None

    url = "https://api.buchbutler.de/CONTENT/"
    params = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "ean": ean
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        res = data.get("response")
        if not res:
            return None

        attrs = res.get("Artikelattribute", {})

        # ⭐ NEU → Lagerdaten laden
        lager = lade_lager_von_api(ean)

        produkt = {
            "id": int(res.get("pim_artikel_id", 0)),
            "name": res.get("bezeichnung"),
            "autor": attrs.get("Autor", {}).get("Wert", ""),
            "preis": float(res.get("vk_brutto") or 0),
            "beschreibung": res.get("text_text") or "",

            # Bild
            "bilder": [f"https://api.buchbutler.de/image/{ean}"],

            # Details
            "isbn": attrs.get("ISBN_13", {}).get("Wert", ""),
            "seiten": attrs.get("Seiten", {}).get("Wert", ""),
            "format": attrs.get("Buchtyp", {}).get("Wert", ""),

            "sprache": attrs.get("Sprache", {}).get("Wert", ""),
            "verlag": attrs.get("Verlag", {}).get("Wert", ""),
            "erscheinungsjahr": attrs.get("Erscheinungsjahr", {}).get("Wert", ""),
            "erscheinungsdatum": attrs.get("Erscheinungsdatum", {}).get("Wert", ""),

            "alter_von": attrs.get("Altersempfehlung_von", {}).get("Wert", ""),
            "alter_bis": attrs.get("Altersempfehlung_bis", {}).get("Wert", ""),
            "lesealter": attrs.get("Lesealter", {}).get("Wert", ""),

            "gewicht": attrs.get("Gewicht", {}).get("Wert", ""),
            "laenge": attrs.get("Laenge", {}).get("Wert", ""),
            "breite": attrs.get("Breite", {}).get("Wert", ""),
            "hoehe": attrs.get("Hoehe", {}).get("Wert", ""),

            # ⭐ NEU → Lager / Versand Infos
            "bestand": lager.get("Bestand") or None,
            "einkaufspreis": lager.get("Einkaufspreis") or None,
            "handling_zeit": lager.get("Handling_Zeit_in_Werktagen") or None,
            "erfuellungsrate": lager.get("Erfuellungsrate") or None,

            "extra": attrs
        }

        return produkt

    except Exception as e:
        logger.error(f"Fehler beim Laden von API: {e}")
        return None

# ---------- SENDGRID KONFIGURATION ----------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

def send_email(subject, body, recipient=EMAIL_SENDER):
    """E-Mail-Versand mit SendGrid"""
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

        if action == "register":
            email = request.form.get("email")
            password = request.form.get("password")

            if not email or not password:
                flash("Bitte alle Felder ausfüllen.", "error")
                return redirect(url_for("login"))

            existing = User.query.filter_by(email=email).first()
            if existing:
                flash("Diese E-Mail ist bereits registriert.", "error")
                return redirect(url_for("login"))

            hashed = generate_password_hash(password)
            new_user = User(email=email, password=hashed)
            db.session.add(new_user)
            db.session.commit()

            flash("Registrierung erfolgreich! Bitte melde dich an.", "success")
            return redirect(url_for("login"))

        elif action == "login":
            email = request.form.get("email")
            password = request.form.get("password")

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

    if produkt and produkt.get("ean"):
        api_produkt = lade_produkt_von_api(produkt["ean"])
        if api_produkt:
            produkt.update(api_produkt)

    if not produkt:
        abort(404)

    return render_template('produkt.html', produkt=produkt, user_email=session.get("user_email"))

# ---------- SEITEN ----------
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

# ---------- CHECKOUT MIT NEWSLETTER ----------
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

# ---------- FORMULARE ----------
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

# ---------- DANKESSEITEN ----------
@app.route('/danke')
def danke():
    return render_template('danke.html', user_email=session.get("user_email"))

@app.route('/kontaktdanke')
def kontaktdanke():
    return render_template('kontaktdanke.html', user_email=session.get("user_email"))

@app.route('/bestelldanke')
def bestelldanke():
    return render_template('bestelldanke.html', user_email=session.get("user_email"))

# ---------- WARENKORB ----------
@app.route('/cart')
def cart():
    cart_items = [
        {'title': 'Reife Blessuren | Danilo Lučić', 'price': 23.90, 'quantity': 1}
    ]
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, user_email=session.get("user_email"))

# ---------- RECHTLICHES ----------

@app.route('/rechtliches')
def rechtliches():
    return render_template('rechtliches.html', user_email=session.get("user_email"))

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html', user_email=session.get("user_email"))

@app.route('/impressum')
def impressum():
    return render_template('impressum.html', user_email=session.get("user_email"))

# ---------- CRON / TEST ----------
@app.route("/cron")
def cron():
    print("Cronjob wurde ausgelöst")
    return "OK"

# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
