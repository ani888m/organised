from flask import Flask, render_template, request, redirect, flash, abort
import os
import json
from dotenv import load_dotenv

# NEU: Imports für SendGrid API (ersetzt smtplib und email.mime)
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To
# Zusätzlicher Import für bessere Fehlerbehandlung
from python_http_client.exceptions import HTTPError 

# ---------- SETUP ----------
load_dotenv()  # nur lokal .env laden
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')

with open(json_path, encoding='utf-8') as f:
    produkte = json.load(f)

app = Flask(__name__)
# Secret Key für Sessions & Flash
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

# Environment Variables für SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
# EMAIL_SENDER MUSS die in SendGrid verifizierte E-Mail-Adresse sein
EMAIL_SENDER = os.getenv("EMAIL_SENDER") 
# Die alte Variable EMAIL_APP_PASSWORD wird nicht mehr verwendet

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
# ---------- KONTAKT FUNKTIONEN (ANGEPASST FÜR SENDGRID) ----------
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
        # Fängt jeden Fehler ab und zeigt ihn dem Benutzer
        flash(f"Fehler beim Senden der Nachricht: {e}", "error")
        return redirect('/kontakt')


def send_email(name, email, message):
    sender_email = EMAIL_SENDER # Ihre verifizierte E-Mail
    recipient_email = EMAIL_SENDER # Sie empfangen die Nachricht

    if not SENDGRID_API_KEY or not sender_email:
        raise ValueError("SENDGRID_API_KEY oder EMAIL_SENDER ist nicht gesetzt!")

    subject = f'Neue Nachricht von {name}'
    body_content = f"Von: {name} <{email}>\n\nNachricht:\n{message}"

    try:
        # Erstelle das Mail-Objekt mit SendGrid-Helfern
        message_to_send = Mail(
            from_email=Email(sender_email),
            to_emails=To(recipient_email),
            subject=subject,
            plain_text_content=body_content
        )
        
        # Sende die E-Mail über die SendGrid API
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.client.mail.send.post(request_body=message_to_send.get())

        if response.status_code >= 200 and response.status_code < 300:
            print(f"E-Mail erfolgreich über SendGrid gesendet! Status: {response.status_code}")
        else:
            # Fehlerhafte API-Antwort, z.B. wenn die FROM-Adresse nicht verifiziert ist.
            error_body = response.body.decode('utf-8') if response.body else "Keine Details verfügbar."
            raise RuntimeError(f"SendGrid API Fehler (Status {response.status_code}): {error_body}")
            
    except HTTPError as e:
        # Fängt spezifische HTTP-Fehler von SendGrid ab
        error_details = e.body.decode('utf-8') if e.body else "Prüfen Sie Ihre API-Schlüssel oder Verifizierung."
        raise RuntimeError(f"SendGrid HTTP-Fehler: Status {e.status_code}. Details: {error_details}")
    except Exception as e:
        raise RuntimeError(f"Allgemeiner Fehler beim Senden der E-Mail: {e}")


# ------------------------------------
# ---------- NEWSLETTER FUNKTIONEN (ANGEPASST FÜR SENDGRID) ----------
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
    sender_email = EMAIL_SENDER
    recipient_email = EMAIL_SENDER

    if not SENDGRID_API_KEY or not sender_email:
        raise ValueError("SENDGRID_API_KEY oder EMAIL_SENDER ist nicht gesetzt!")

    subject = 'Neue Newsletter-Anmeldung'
    body_content = f'Neue Newsletter-Anmeldung:\n\n{email}'

    try:
        # Erstelle das Mail-Objekt mit SendGrid-Helfern
        message_to_send = Mail(
            from_email=Email(sender_email),
            to_emails=To(recipient_email),
            subject=subject,
            plain_text_content=body_content
        )
        
        # Sende die E-Mail über die SendGrid API
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.client.mail.send.post(request_body=message_to_send.get())
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"Newsletter-Benachrichtigung erfolgreich über SendGrid gesendet! Status: {response.status_code}")
        else:
            error_body = response.body.decode('utf-8') if response.body else "Keine Details verfügbar."
            raise RuntimeError(f"SendGrid API Fehler (Status {response.status_code}): {error_body}")

    except HTTPError as e:
        error_details = e.body.decode('utf-8') if e.body else "Prüfen Sie Ihre API-Schlüssel oder Verifizierung."
        raise RuntimeError(f"SendGrid HTTP-Fehler: Status {e.status_code}. Details: {error_details}")
    except Exception as e:
        raise RuntimeError(f"Allgemeiner Fehler beim Senden der Newsletter-Benachrichtigung: {e}")


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
