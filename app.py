from flask import Flask, render_template, request, redirect, flash, abort, session, url_for
import os
import json
from dotenv import load_dotenv
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# ---------- SETUP ----------
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')
db_path = os.path.join(basedir, "users.db")

with open(json_path, encoding='utf-8') as f:
    produkte = json.load(f)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# ---------- Hilfsfunktion ----------
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
        logger.info(f"E-Mail erfolgreich an {recipient} gesendet! Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail: {e}")
        raise RuntimeError(f"Fehler beim Senden der E-Mail: {e}")

# ---------- ROUTES ----------
@app.route('/')
def index():
    kategorienamen = [
        "Unsere Bücher", "Neuerscheinungen", "Über Angst", "Helga Bansch",
        "Klassiker", "Monstergeschichten", "Über Farben", "Weihnachten",
        "Kinder und ihre Gefühle"
    ]
    kategorien = [(k, [p for p in produkte if p.get("kategorie") == k]) for k in kategorienamen]
    user = session.get("user")
    return render_template("index.html", kategorien=kategorien, user=user)

@app.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)
    if produkt is None:
        abort(404)
    return render_template('produkt.html', produkt=produkt)

@app.route('/team')
def team():
    return render_template('Team.html')

@app.route('/vision')
def vision():
    return render_template('vision.html')

@app.route('/presse')
def presse():
    return render_template('presse.html')

@app.route('/kontakt')
def kontakt():
    return render_template('kontakt.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    return render_template('checkout.html')

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

@app.route('/danke')
def danke():
    return render_template('danke.html')

@app.route('/kontaktdanke')
def kontaktdanke():
    return render_template('kontaktdanke.html')

@app.route('/cart')
def cart():
    cart_items = [
        {'title': 'Reife Blessuren | Danilo Lučić', 'price': 23.90, 'quantity': 1}
    ]
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/success')
def success():
    return "Danke für deinen Einkauf!"

@app.route('/cancel')
def cancel():
    return "Bezahlung abgebrochen."

@app.route('/rechtliches')
def rechtliches():
    return render_template('rechtliches.html')

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user"] = username
            flash(f"Willkommen, {username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Ungültiger Benutzername oder Passwort.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

# ---------- REGISTRIERUNG ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not password:
            flash("Bitte alle Felder ausfüllen!", "error")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
            conn.commit()
            flash("Registrierung erfolgreich! Du kannst dich jetzt einloggen.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Benutzername existiert bereits.", "error")
        finally:
            conn.close()

    return render_template("register.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Du wurdest erfolgreich ausgeloggt.", "info")
    return redirect(url_for("index"))

# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
