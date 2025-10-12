from flask import Flask, render_template, request, redirect, flash, abort
from flask_sqlalchemy import SQLAlchemy
import os
import json
from dotenv import load_dotenv

# ---------- SETUP ----------
load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, 'produkte.json')

# Produkte laden
try:
    with open(json_path, encoding='utf-8') as f:
        produkte = json.load(f)
except Exception as e:
    print("Fehler beim Laden von produkte.json:", e)
    produkte = []

# Flask & Datenbank konfigurieren
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

# SQLite-Datenbank im Projektverzeichnis
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///datenbank.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- MODELLE ----------
class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Kontaktanfrage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

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

@app.route("/rechtliches")
def rechtliches():
    return render_template("rechtliches.html")

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

# ---------- KONTAKT ----------
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    if not name or not email or not message:
        flash("Bitte fülle alle Felder aus.", "error")
        return redirect('/kontakt')

    try:
        eintrag = Kontaktanfrage(name=name, email=email, message=message)
        db.session.add(eintrag)
        db.session.commit()
        flash("Danke! Deine Nachricht wurde gespeichert.", "success")
        return redirect('/kontakt')
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Speichern der Nachricht: {e}", "error")
        return redirect('/kontakt')

# ---------- NEWSLETTER ----------
@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email')

    if not email:
        flash('Bitte gib eine gültige E-Mail-Adresse ein.', 'error')
        return redirect('/')

    try:
        if Newsletter.query.filter_by(email=email).first():
            flash("Du bist bereits angemeldet.", "info")
        else:
            eintrag = Newsletter(email=email)
            db.session.add(eintrag)
            db.session.commit()
            flash("Danke! Newsletter-Anmeldung erfolgreich gespeichert.", "success")
        return redirect('/danke')
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Speichern der Anmeldung: {e}", "error")
        return redirect('/')

@app.route('/danke')
def danke():
    return render_template('danke.html')

# ---------- START ----------


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

