from flask import Blueprint, render_template, abort, session, current_app
from services.buchbutler import lade_produkt_von_api, lade_bestand_von_api
from services.mail import send_email
import json
import os

shop_bp = Blueprint("shop", __name__)

# ----------------------------
# Produkte laden
# ----------------------------
basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, "../produkte.json")

if os.path.exists(json_path):
    with open(json_path, encoding='utf-8') as f:
        produkte = json.load(f)
else:
    produkte = []


# ----------------------------
# Startseite / Kategorien
# ----------------------------
@shop_bp.route('/')
def index():
    kategorienamen = [
        "Jacominus Gainsborough", "Mut oder Angst?!",
        "Klassiker", "Monstergeschichten", "Wichtige Fragen", "Weihnachten",
        "Kinder und Gefühle", "Dazugehören"
    ]
    kategorien = [(k, [p for p in produkte if p.get("kategorie") == k]) for k in kategorienamen]
    return render_template("index.html", kategorien=kategorien, user_email=session.get("user_email"))


# ----------------------------
# Produktdetailseite
# ----------------------------
@shop_bp.route('/produkt/<int:produkt_id>')
def produkt_detail(produkt_id):
    produkt = next((p for p in produkte if p['id'] == produkt_id), None)
    if not produkt:
        abort(404)

    if produkt.get("ean"):
        api_produkt = lade_produkt_von_api(produkt["ean"])
        if api_produkt:
            produkt.update(api_produkt)

        movement = lade_bestand_von_api(produkt["ean"])
        if movement:
            produkt.update(movement)

    produkt.setdefault("bestand", "n/a")
    produkt.setdefault("preis", 0)
    produkt.setdefault("handling_zeit", "n/a")
    produkt.setdefault("erfuellungsrate", "n/a")

    return render_template('produkt.html', produkt=produkt, user_email=session.get("user_email"))


# ----------------------------
# Warenkorb
# ----------------------------
@shop_bp.route('/cart')
def cart():
    cart_items = [
        {'title': 'Reife Blessuren | Danilo Lučić', 'price': 23.90, 'quantity': 1}
    ]
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, user_email=session.get("user_email"))


# ----------------------------
# Checkout
# ----------------------------
@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    from flask import request, flash, redirect, url_for

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        newsletter = request.form.get('newsletter')
        payment_method = request.form.get('payment-method')

        if not name or not email or not payment_method:
            flash("Bitte fülle alle Pflichtfelder aus.", "error")
            return redirect(url_for('shop.checkout'))

        if newsletter:
            try:
                send_email(
                    subject='Neue Newsletter-Anmeldung (über Bestellung)',
                    body=f'{name} ({email}) hat sich beim Bestellvorgang für den Newsletter angemeldet.'
                )
            except Exception as e:
                current_app.logger.warning(f"Newsletter konnte nicht gesendet werden: {e}")

        flash("Zahlung erfolgreich (Simulation). Vielen Dank für deine Bestellung!", "success")
        return redirect(url_for('shop.danke'))

    return render_template('checkout.html', user_email=session.get("user_email"))


# ----------------------------
# Danke-Seite nach Checkout
# ----------------------------
@shop_bp.route('/danke')
def danke():
    return render_template('bestelldanke.html', user_email=session.get("user_email"))
