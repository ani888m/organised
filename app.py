from flask import Flask, render_template, request, redirect, flash, url_for, abort
import smtplib
from email.mime.text import MIMEText
import stripe
import os
import json



# JSON-Datei laden (einmalig)
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')

with open(json_path, encoding='utf-8') as f:
    produkte = json.load(f)


app = Flask(__name__)
app.secret_key = 'irgendetwasgeheimes'  # wichtig für Flash-Messages

# Stripe API Key aus Umgebungsvariable (nicht im Code speichern)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "DEIN_STRIPE_SECRET_KEY")


# ---------- SEITEN ----------
@app.route('/')
def index():
  neuerscheinungen = produkte[4:8]

    return render_template('index.html', produkte=produkte, neuerscheinungen=neuerscheinungen
)

@app.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)
    if produkt is None:
        abort(404)
    return render_template('produkt.html', produkt=produkt)
    
@app.route('/')
def home():
    return render_template('index.html')

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

@app.route("/newsletter-snippet")
def newsletter_snippet():
    return render_template("newsletter.html")
    

# GET und POST in einer Funktion: checkout-Seite und Zahlung starten
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
        return render_template('checkout.html')


# ---------- KONTAKT ----------
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    send_email(name, email, message)
    return "Danke! Deine Nachricht wurde gesendet."


def send_email(name, email, message):
    sender = 'antonyan125@gmail.com'
    app_password = 'ffutcvkflhcgiijl'
    recipient = 'antonyan125@gmail.com'

    subject = f'Neue Nachricht von {name}'
    body = f"Von: {name} <{email}>\n\nNachricht:\n{message}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print("E-Mail gesendet!")
    except Exception as e:
        print("Fehler beim Senden:", e)


# ---------- NEWSLETTER ----------
@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email')

    if not email:
        flash('Bitte gib eine gültige E-Mail-Adresse ein.', 'error')
        return redirect('/')

    try:
        send_newsletter_email(email)
        return redirect('/danke')
    except Exception as e:
        print("Fehler beim Newsletter-Versand:", e)
        flash('Es gab ein Problem bei der Anmeldung.', 'error')
        return redirect('/')


@app.route('/danke')
def danke():
    return render_template('danke.html')


def send_newsletter_email(email):
    sender = 'antonyan125@gmail.com'
    app_password = 'ffutcvkflhcgiijl'
    recipient = 'antonyan125@gmail.com'

    subject = 'Neue Newsletter-Anmeldung'
    body = f'Neue Newsletter-Anmeldung:\n\n{email}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print("Newsletter-Benachrichtigung gesendet!")
    except Exception as e:
        print("Fehler beim Senden der Newsletter-Benachrichtigung:", e)


# ---------- WARENKORB & ZAHLUNG ----------
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


# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
