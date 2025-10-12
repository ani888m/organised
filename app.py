from flask import Flask, render_template, request, redirect, flash, abort
import smtplib
from email.mime.text import MIMEText
import os
import json
from dotenv import load_dotenv  # optional für lokale Tests

# ---------- SETUP ----------
load_dotenv()  # nur lokal .env laden
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')

with open(json_path, encoding='utf-8') as f:
    produkte = json.load(f)

app = Flask(__name__)
# Secret Key für Sessions & Flash
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

# Gmail-Zugangsdaten aus Environment Variables
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# ---------- SEITEN ----------
@app.route('/')
def index():
    kategorienamen = [
        "Unsere Bücher", "Neuerscheinungen", "Über Angst", "Helga Bansch",
        "Klassiker", "Monstergeschichten", "Über Farben", "Weihnachten",
        "Kinder und ihre Gefühle"
    ]

    kategorien = [
        (k, [p for p in produkte if p.get("kategorie") == k])
        for k in kategorienamen
    ]

    return render_template("index.html", kategorien=kategorien)


@app.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)
    if produkt is None:
        abort(404)
    return render_template('produkt.html', produkt=produkt)


@app.route('/navbar')
def navbar():
    return render_template('navbar.html')


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


# ------------------------------------
# ---------- KONTAKT FUNKTIONEN ----------
# ------------------------------------
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    try:
        send_email(name, email, message)
        flash("Danke! Deine Nachricht wurde gesendet.", "success")
        return redirect('/kontakt')
    except Exception as e:
        # Fängt jeden Fehler ab, einschließlich des Timeouts
        flash(f"Fehler beim Senden der Nachricht: {e}", "error")
        return redirect('/kontakt')


def send_email(name, email, message):
    sender = EMAIL_SENDER
    app_password = EMAIL_APP_PASSWORD
    recipient = EMAIL_SENDER

    if not sender or not app_password:
        raise ValueError("EMAIL_SENDER oder EMAIL_APP_PASSWORD ist nicht gesetzt!")

    subject = f'Neue Nachricht von {name}'
    body = f"Von: {name} <{email}>\n\nNachricht:\n{message}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        # *** ANPASSUNG HIER: Wechsel zu Port 587 und starttls() ***
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Starte die verschlüsselte Verbindung
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        print("E-Mail erfolgreich gesendet!")
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP Authentication Error: Überprüfe EMAIL_SENDER und EMAIL_APP_PASSWORD!")
    except Exception as e:
        # Fängt den Verbindungsfehler (Timeout) ab
        raise RuntimeError(f"Fehler beim Senden der E-Mail (wahrscheinlich Verbindung): {e}")


# ------------------------------------
# ---------- NEWSLETTER FUNKTIONEN ----------
# ------------------------------------
@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email')

    if not email:
        flash('Bitte gib eine gültige E-Mail-Adresse ein.', 'error')
        return redirect('/')

    try:
        send_newsletter_email(email)
        flash("Danke! Newsletter-Anmeldung erfolgreich.", "success")
        return redirect('/danke')
    except Exception as e:
        flash(f"Fehler beim Newsletter-Versand: {e}", "error")
        return redirect('/')


@app.route('/danke')
def danke():
    return render_template('danke.html')


def send_newsletter_email(email):
    sender = EMAIL_SENDER
    app_password = EMAIL_APP_PASSWORD
    recipient = EMAIL_SENDER

    if not sender or not app_password:
        raise ValueError("EMAIL_SENDER oder EMAIL_APP_PASSWORD ist nicht gesetzt!")

    subject = 'Neue Newsletter-Anmeldung'
    body = f'Neue Newsletter-Anmeldung:\n\n{email}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        # *** ANPASSUNG HIER: Wechsel zu Port 587 und starttls() ***
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Starte die verschlüsselte Verbindung
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        print("Newsletter-Benachrichtigung erfolgreich gesendet!")
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP Authentication Error: Überprüfe EMAIL_SENDER und EMAIL_APP_PASSWORD!")
    except Exception as e:
        # Fängt den Verbindungsfehler (Timeout) ab
        raise RuntimeError(f"Fehler beim Senden der Newsletter-Benachrichtigung (wahrscheinlich Verbindung): {e}")


# ------------------------------------
# ---------- WARENKORB & RECHTLICHES ----------
# ------------------------------------
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


@app.route("/rechtliches")
def rechtliches():
    return render_template("rechtliches.html")


# ---------- START ----------
if __name__ == '__main__':
    # Fügt Logging hinzu, um die Fehlerbehebung zu erleichtern
    import logging
    logging.basicConfig(level=logging.INFO) 
    app.run(debug=True)
