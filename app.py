from flask import Flask, render_template, request, redirect, flash, abort, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from dotenv import load_dotenv
import logging
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

        # 🔹 Registrierung
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

        # 🔹 Login
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
    if produkt is None:
        abort(404)
    return render_template('produkt.html', produkt=produkt, user_email=session.get("user_email"))


# ---------- SEITEN ----------
@app.route('/navbar')
def navbar():
    return render_template('navbar.html', user_email=session.get("user_email"))




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

        # Falls Newsletter ausgewählt wurde → sende E-Mail im Hintergrund
        if newsletter:
            try:
                send_email(
                    subject='Neue Newsletter-Anmeldung (über Bestellung)',
                    body=f'{name} ({email}) hat sich beim Bestellvorgang für den Newsletter angemeldet.'
                )
                # kein Redirect — Nutzer bleibt auf der Bestell-Danke-Seite
            except Exception as e:
                logger.warning(f"Newsletter konnte nicht gesendet werden: {e}")

        # Bestellung bestätigen (Simulation)
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
        flash(f"Fehler beim Newsletter-Versand: {e}", "error")
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
    
@app.route("/cron")
def cron():
    print("Cronjob wurde ausgelöst")
    return "OK"



# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
