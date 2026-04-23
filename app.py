import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
import uuid


from flask import (
    Flask, render_template, request,
    redirect, flash, abort,
    session, url_for, jsonify
)

from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Modelle importieren
from models import db, Bestellung, BestellPosition, NewsletterSubscriber


from datetime import timedelta

from functools import lru_cache

import re




# =====================================================
# CONFIG
# =====================================================

load_dotenv()

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)

PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")

PAYPAL_BASE = (
    "https://api-m.sandbox.paypal.com"
    if PAYPAL_MODE == "sandbox"
    else "https://api-m.paypal.com"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = False

app.config["PAYPAL_CLIENT_ID"] = PAYPAL_CLIENT_ID


app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY fehlt!")

database_url = os.getenv("DATABASE_URL", "sqlite:///ibk-shop-db.db")
database_url = database_url.replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
with app.app_context():
    db.create_all()






ADMIN_PASSWORD = os.getenv("FLASK_ADMIN_PASSWORD")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

csrf = CSRFProtect(app)



# ---------- BUCHBUTLER API ZUGANG ----------



BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")

BUCHBUTLER_MOL_KUNDE_ID = os.getenv("BUCHBUTLER_MOL_KUNDE_ID")
BUCHBUTLER_RECHNUNGSADRESSE_ID = os.getenv("BUCHBUTLER_RECHNUNGSADRESSE_ID", "1")
BUCHBUTLER_VERKAUFSKANAL_ID = os.getenv("BUCHBUTLER_VERKAUFSKANAL_ID", "1")

BASE_URL = "https://api.buchbutler.de"



# =====================================================
# PRODUKTE LADEN
# =====================================================

basedir = os.path.abspath(os.path.dirname(__file__))
json_path = os.path.join(basedir, "produkte.json")

if os.path.exists(json_path):
    with open(json_path, encoding="utf-8") as f:
        produkte = json.load(f)
else:
    produkte = []


# =====================================================
# LOGIN
# =====================================================


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            flash("E-Mail existiert bereits", "error")
            return redirect("/register")

        user = User(email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id

        return redirect("/")

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
@csrf.exempt
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Login fehlgeschlagen", "error")
            return redirect("/login")

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")





@app.context_processor
def inject_user():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return dict(current_user=user)


@app.route("/meine-gutscheine")
def meine_gutscheine():
    if "user_id" not in session:
        return redirect("/login")

    gutscheine = Gutschein.query.filter_by(user_id=session["user_id"]).all()

    return render_template("gutscheine.html", gutscheine=gutscheine)


def update_user_punkte_und_gutschein(user, cart_items):
    """Fügt Punkte hinzu und vergibt ggf. Gutschein"""
    punkte = int(calculate_total(cart_items))
    user.punkte += punkte

    # 🎁 Gutschein bei 100 Punkten
    if user.punkte >= 100:
        code = str(uuid.uuid4())[:8]
        gutschein = Gutschein(
            code=code,
            wert=10,  # z.B. 10€
            user_id=user.id
        )
        user.punkte -= 100
        db.session.add(gutschein)

        send_email(
            subject="Dein Gutschein 🎁",
            body=f"Dein Code: {code}",
            recipient=user.email
        )

    db.session.commit()

# =====================================================
# PAYPAL
# =====================================================

def paypal_access_token():
    response = requests.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"},
    )
    return response.json().get("access_token")





@app.route("/create-paypal-order", methods=["POST"])
@csrf.exempt
def create_paypal_order():
    cart_items = get_cart()
    total = calculate_total(cart_items)

    if not cart_items or total <= 0:
        return jsonify({"error": "Warenkorb leer"}), 400

    access_token = paypal_access_token()

    response = requests.post(
        f"{PAYPAL_BASE}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "EUR",
                    "value": f"{total:.2f}"
                }
            }]
        },
    )

    order_data = response.json()
    return jsonify({"id": order_data["id"]})




@app.route("/capture-paypal-order/<order_id>", methods=["POST"])
@csrf.exempt
def capture_paypal_order(order_id):
    try:
        access_token = paypal_access_token()

        response = requests.post(
            f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
        )

        data = response.json()

        if data.get("status") != "COMPLETED":
            return jsonify({"status": "error", "message": "PayPal-Zahlung nicht abgeschlossen", "data": data}), 400

        cart_items = get_cart()

        bestellung = Bestellung(
            email=session.get("checkout_email"),
            vorname=session.get("checkout_vorname"),
            nachname=session.get("checkout_nachname"),
            strasse=session.get("checkout_strasse"),
            hausnummer=session.get("checkout_hausnummer"),
            plz=session.get("checkout_plz"),
            stadt=session.get("checkout_stadt"),
            land=session.get("checkout_land"),
            telefon=session.get("checkout_telefon"),
            paymentmethod="paypal"
        )

        db.session.add(bestellung)
        db.session.flush()

        for item in cart_items:
            db.session.add(
                BestellPosition(
                    bestellung_id=bestellung.id,
                    bezeichnung=item["title"],
                    menge=item["quantity"],
                    preis=item["price"]
                )
            )

        db.session.commit()

        try:
            sende_bestellung_an_buchbutler(bestellung, cart_items)
        except Exception:
            logger.exception("Buchbutler Bestellung fehlgeschlagen")

        # Warenkorb leeren
        session.pop("cart", None)

        return jsonify({"status": "success", "order_id": order_id})

    except Exception as e:
        logger.exception("Fehler beim Capturen der PayPal-Zahlung")
        return jsonify({"status": "error", "message": str(e)}), 500

def verify_webhook(headers, body):

    access_token = paypal_access_token()

    response = requests.post(
        f"{PAYPAL_BASE}/v1/notifications/verify-webhook-signature",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
            "cert_url": headers.get("PAYPAL-CERT-URL"),
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": body
        }
    )

    return response.json().get("verification_status") == "SUCCESS"



@app.route("/paypal-webhook", methods=["POST"])
@csrf.exempt
def paypal_webhook():

    body = request.get_data(as_text=True)
    event = json.loads(body)
    headers = request.headers

    if not verify_webhook(headers, body):
        return "", 400

    event_type = body.get("event_type")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture = event["resource"]
        order_id = capture["supplementary_data"]["related_ids"]["order_id"]
        amount = capture["amount"]["value"]
        logger.info(f"PayPal Zahlung abgeschlossen: {order_id} – {amount} EUR")



    return "", 200


# =====================================================
# HILFSFUNKTIONEN
# =====================================================

def get_cart():
    return session.get("cart", [])

def save_cart(cart):
    session["cart"] = cart
    session.modified = True

def calculate_total(cart):
    return sum(item["price"] * item["quantity"] for item in cart)


def check_auth():
    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        logger.error("Buchbutler Zugangsdaten fehlen")
        return False
    return True


def to_float(value):
    """Konvertiert API Preis sicher"""
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def to_int(value):
    """Konvertiert Zahlen sicher"""
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def attr(attrs, key):
    """Greift sicher auf Artikelattribute zu"""
    return (attrs.get(key) or {}).get("Wert", "")

def buchbutler_request(endpoint, ean):
    """Allgemeine Request Funktion"""
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
# -----------------------------
# CONTENT API
# -----------------------------

@lru_cache(maxsize=128)
def cached_lade_produkt_von_api(ean):
    return lade_produkt_von_api(ean)

def lade_produkt_von_api(ean):
    """Lädt Produktdaten von CONTENT API"""

    if not check_auth():
        return None

    try:
        res = buchbutler_request("CONTENT", ean)

        if not res:
            return None

        attrs = res.get("Artikelattribute") or {}

        produkt = {
            "id": to_int(res.get("pim_artikel_id")),
            "name": res.get("bezeichnung"),
            "autor": attr(attrs, "Autor"),
            "illustrator": attr(attrs, "Illustrator"),
            "preis": to_float(res.get("vk_brutto")),
           
            "isbn": attr(attrs, "ISBN_13"),
            "seiten": attr(attrs, "Seiten"),
            "format": attr(attrs, "Buchtyp"),
            "sprache": attr(attrs, "Sprache"),
            "verlag": attr(attrs, "Verlag"),
            "erscheinungsjahr": attr(attrs, "Erscheinungsjahr"),
            "erscheinungsdatum": attr(attrs, "Erscheinungsdatum"),
            "alter_von": attr(attrs, "Altersempfehlung_von"),
            "alter_bis": attr(attrs, "Altersempfehlung_bis"),
            "lesealter": attr(attrs, "Lesealter"),
            "gewicht": attr(attrs, "Gewicht"),
            "laenge": attr(attrs, "Laenge"),
            "breite": attr(attrs, "Breite"),
            "hoehe": attr(attrs, "Hoehe"),
            "extra": attrs
        }

        return produkt

    except Exception:
        logger.exception("Fehler beim Laden von CONTENT API")
        return None

# -----------------------------
# MOVEMENT API
# -----------------------------

def lade_bestand_von_api(ean):
    """Lädt Bestand / Preis / Lieferdaten"""

    if not check_auth():
        return None

    try:
        res = buchbutler_request("MOVEMENT", ean)

        if not res:
            return None

        # 🔥 FIX — falls Liste zurückkommt
        if isinstance(res, list):
            if len(res) == 0:
                return None
            res = res[0]

        return {
            "bestand": to_int(res.get("Bestand")),
            "preis": to_float(res.get("Preis")),
            "erfuellungsrate": res.get("Erfuellungsrate"),
            "handling_zeit": res.get("Handling_Zeit_in_Werktagen")

        }


    except Exception:
        logger.exception("Fehler beim Laden von MOVEMENT API")
        return None

# -----------------------------
# Bestellung an Buchbutler senden 
# -----------------------------

def sende_bestellung_an_buchbutler(bestellung, cart_items):

    url = f"{BASE_URL}/ORDER/"

    collectkey = str(uuid.uuid4())
    bestellung.collectkey = collectkey
    db.session.commit()

    payload = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,

        "auftrag_kopf": {
            "mol_kunde_id": int(BUCHBUTLER_MOL_KUNDE_ID),
            "rechnungsadresse_id": int(BUCHBUTLER_RECHNUNGSADRESSE_ID),
            "mol_zahlart_id": 2,  # PayPal
            "bestelldatum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bestellreferenz": f"IBK-{bestellung.id}",
            "seite": "ibk-bilderbuch.de",
            "bestellfreigabe": 1,
            "mol_verkaufskanal_id": int(BUCHBUTLER_VERKAUFSKANAL_ID)
        },

        "lieferadresse": {
            "anrede": "",
            "vorname": bestellung.vorname,
            "nachname": bestellung.nachname,
            "strasse": bestellung.strasse,
            "hausnummer": bestellung.hausnummer,
            "plz": bestellung.plz,
            "ort": bestellung.stadt,
            "land": bestellung.land,
            "land_iso": "DE",
            "tel": bestellung.telefon
        },

        "auftrag_position": [],

        "auftrag_zusatz": [
            {
                "typ": "SHIPPING_OPTION",
                "value": "1040"
            },
            {
                "typ": "collectkey",
                "value": collectkey
            }
        ]
    }

    

    for i, item in enumerate(cart_items):
        payload["auftrag_position"].append({
            "ean": item["ean"],
            "pos_bezeichnung": item["title"],
            "menge": item["quantity"],
            "ek_netto": 0,
            "vk_brutto": item["price"],
            "pos_referenz": f"{bestellung.id}-{i}"
        })
    
    response = requests.post(url, json=payload, timeout=20)
    
    data = response.json()
    
    if data.get("import_hash"):
        bestellung.moluna_order_id = data["import_hash"]
        bestellung.moluna_status = "übermittelt"
        db.session.commit()
        
    logger.info("Buchbutler Bestellung: %s", data)
    return data
    
    
def buchbutler_orderresponse(collectkey):

    url = f"{BASE_URL}/ORDERRESPONSE/"

    payload = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "collectkey": collectkey
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        # Wenn keine erfolgreiche Antwort
        if response.status_code != 200:
            logger.warning(f"ORDERRESPONSE Statuscode: {response.status_code}")
            return None

        # Wenn Antwort leer ist
        if not response.text.strip():
            logger.info("ORDERRESPONSE leer")
            return None

        return response.json()

    except Exception:
        logger.exception("ORDERRESPONSE Fehler")
        return None
# =====================================================
# ROUTES
# =====================================================

# Admin Test
@app.route("/admin-test")
def admin_test():
    alle = Bestellung.query.all()
    return {"anzahl_bestellungen": len(alle)}



def admin_required():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return None



@limiter.limit("5 per minute")
@app.route("/ibk-control-8471", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password")
        if pw == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            session.permanent = True
            return redirect("/admin/bestellungen")
        else:
            flash("Falsches Passwort!", "error")
    return render_template("admin_login.html")



# Admin Bestellungen anzeigen




@app.route("/admin/bestellungen")
def admin_bestellungen():

    resp = admin_required()
    if resp:
        return resp

    alle = Bestellung.query.order_by(Bestellung.bestelldatum.desc()).all()

    for b in alle:

        if getattr(b, "collectkey", None):

            response = buchbutler_orderresponse(b.collectkey)

            if response and "response" in response:
                status = response["response"].get("status")
                lieferungen = response["response"].get("lieferungen", [])

                # Status speichern
                b.moluna_status = status if status else "unbekannt"

                # Trackingnummern & andere Felder sammeln
                trackingnummern = []
                logistiker_list = []
                paketart_list = []
                eans = []

                for lieferung in lieferungen:
                    if lieferung.get("trackingnummer"):
                        trackingnummern.append(lieferung["trackingnummer"])
                    if lieferung.get("logistiker"):
                        logistiker_list.append(lieferung["logistiker"])
                    if lieferung.get("logistik_produkt"):
                        paketart_list.append(lieferung["logistik_produkt"])
                    if lieferung.get("ean"):
                        eans.append(lieferung["ean"])

                # Optional: als kommagetrennte Strings speichern
                b.trackingnummer = ", ".join(trackingnummern) if trackingnummern else None
                b.logistiker = ", ".join(logistiker_list) if logistiker_list else None
                b.paketart = ", ".join(paketart_list) if paketart_list else None
                b.eans = ", ".join(eans) if eans else None

            else:
                b.moluna_status = "keine Antwort"
                b.trackingnummer = None
                b.logistiker = None
                b.paketart = None
                b.eans = None

    # Commit nach allen Updates
    db.session.commit()

    return render_template(
        "admin_bestellungen.html",
        bestellungen=alle
    )


@app.route("/admin/sync-buchbutler/<int:index>")
def sync_buchbutler(index):

    if not session.get("admin"):
        abort(403)

    if index >= len(produkte):
        return "✅ Sync komplett"

    produkt = produkte[index]
    ean = produkt.get("ean")

    if ean:
        print("SYNC:", ean)

        api = lade_produkt_von_api(ean)
        movement = lade_bestand_von_api(ean)

        if api:
            produkt["name"] = api.get("name")
            produkt["autor"] = api.get("autor")

        if movement:
            produkt["preis"] = movement.get("preis")

        # sofort speichern → kein RAM Wachstum
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(produkte, f, ensure_ascii=False, indent=2)

    next_index = index + 1

    return redirect(url_for("sync_buchbutler", index=next_index))
    
# suche icon 
@app.route("/suche", methods=["GET", "POST"])
def suche():
    query = ""
    ergebnisse = []

    if request.method == "POST":
        query = request.form.get("q", "").lower()

        for produkt in produkte:
            name = produkt.get("name", "").lower()

            if query in name:
                ergebnisse.append(produkt)

    return render_template(
        "suche.html",
        query=query,
        ergebnisse=ergebnisse
    )

# Produkt Detail

  
def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9äöüß ]', '', text)
    return text.replace(" ", "-")

for p in produkte:
    p["slug"] = slugify(p.get("name", "produkt"))
    
@app.route('/produkt/<int:produkt_id>/<slug>')
def produkt_detail(produkt_id, slug):

    lokale_daten = next(
        (p.copy() for p in produkte if p["id"] == produkt_id),
        None
    )

    if not lokale_daten:
        abort(404)

    # ✅ richtigen slug berechnen
    richtiger_slug = lokale_daten.get("slug")

    # 🔥 WICHTIG: redirect wenn falsch
    if slug != richtiger_slug:
        return redirect(url_for(
            "produkt_detail",
            produkt_id=produkt_id,
            slug=richtiger_slug
        ), code=301)

    ean = lokale_daten.get("ean")

    if not ean:
        abort(404)

    produkt = cached_lade_produkt_von_api(ean)

    if not produkt:
        abort(404)

    movement = lade_bestand_von_api(ean)
    if movement:
        produkt.update(movement)

    produkt.update(lokale_daten)

    produkt.setdefault("bestand", "n/a")
    produkt.setdefault("preis", 0)
    produkt.setdefault("handling_zeit", "n/a")
    produkt.setdefault("erfuellungsrate", "n/a")

    return render_template(
        "produkt.html",
        produkt=produkt
    )

# ============================
# CART ROUTES
# ============================

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    produkt_id = int(request.form.get("produkt_id"))
    produkt = next((p for p in produkte if p["id"] == produkt_id), None)

    if not produkt:
        abort(404)

    # ✅ WICHTIG: Kopie machen (kein globales Update!)
    produkt = produkt.copy()

    # ✅ Preis + Bestand laden
    if produkt.get("ean"):
        movement = lade_bestand_von_api(produkt["ean"])
        if movement:
            produkt.update(movement)

    cart = get_cart()

    found = False
    for item in cart:
        if item["id"] == produkt_id:
            item["quantity"] += 1
            found = True
            break

  

    if not found:
        cart.append({
            "id": produkt["id"],
            "title": produkt["name"],
            "price": produkt.get("preis", 0),
            "quantity": 1,
            "ean": produkt["ean"]
        })
        

    save_cart(cart)
    return redirect(url_for("cart"))



@app.route("/cart")
def cart():
    cart_items = get_cart()
    total = calculate_total(cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/remove-from-cart/<int:produkt_id>")
def remove_from_cart(produkt_id):
    cart = get_cart()
    cart = [item for item in cart if item["id"] != produkt_id]
    save_cart(cart)
    return redirect(url_for("cart"))


@app.route("/sync-cart", methods=["POST"])
@csrf.exempt  
def sync_cart():
    data = request.get_json()

    if not data:
        return {"status": "error"}, 400

    session["cart"] = data
    session.modified = True

    print("SYNCED CART:", session["cart"])

    return {"status": "ok"}
    
# ============================
# CHECKOUT
# ============================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_items = get_cart()
    total = calculate_total(cart_items)

    logger.info("Checkout gestartet")

    if request.method == "POST":

        email = request.form.get("email")

        if not email or not cart_items:
            flash("Bitte gültige Daten eingeben.", "error")
            return redirect(url_for("checkout"))


         # Kunde erfassen / Punkte vergeben
        if "user_id" in session:
            user = User.query.get(session["user_id"])
            punkte = int(total)  # Beispiel: 1€ = 1 Punkt
            user.punkte += punkte

            # Gutschein vergeben bei 100 Punkten
            if user.punkte >= 100:
                code = str(uuid.uuid4())[:8]
                gutschein = Gutschein(code=code, wert=10, user_id=user.id)
                user.punkte -= 100
                db.session.add(gutschein)
                send_email(
                    subject="Dein Gutschein 🎁",
                    body=f"Dein Code: {code}",
                    recipient=user.email
                )
            db.session.commit()

        try:
            session["checkout_email"] = request.form.get("email")
            session["checkout_vorname"] = request.form.get("vorname")
            session["checkout_nachname"] = request.form.get("nachname")
            session["checkout_strasse"] = request.form.get("strasse")
            session["checkout_hausnummer"] = request.form.get("hausnummer")
            session["checkout_plz"] = request.form.get("plz")
            session["checkout_stadt"] = request.form.get("stadt")
            session["checkout_land"] = request.form.get("land")
            session["checkout_telefon"] = request.form.get("telefon")
            session["checkout_adresszusatz"] = request.form.get("adresszusatz")

            logger.info("Kundendaten für PayPal gespeichert")

        except Exception as e:
            logger.error(f"Checkout Fehler: {e}")
            flash("Fehler beim Checkout.", "error")
            return redirect(url_for("checkout"))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )

# ============================
# KONTAKT
# ============================

@app.route("/kontakt")  
def kontakt():
    return render_template("kontakt.html", user_email=session.get("user_email"))

@app.route("/submit", methods=["POST"])
@csrf.exempt
def submit():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")
    if not name or not email or not message:
        flash("Bitte fülle alle Felder aus!", "error")
        return redirect("/kontakt")
    try:
        send_email(
            subject=f"Neue Nachricht von {name}",
            recipient=EMAIL_SENDER,
            html=f"""
                <p><b>Von:</b> {name} ({email})</p>
                <p>{message}</p>
            """,
            plain_text=f"Von: {name} <{email}>\n\n{message}"
        )
        flash("Danke! Deine Nachricht wurde gesendet.", "success")
    except Exception as e:
        flash(f"Fehler beim Senden: {e}", "error")
    return redirect("/kontaktdanke")

# ============================
# NEWSLETTER
# ============================


def send_email(subject, recipient, html, plain_text=None):
    if not SENDGRID_API_KEY or not EMAIL_SENDER:
        logger.warning("SendGrid nicht konfiguriert")
        return

    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient,
        subject=subject,
        html_content=html,
        plain_text_content=plain_text
    )

    sg = SendGridAPIClient(SENDGRID_API_KEY)

    try:
        sg.send(message)
    except Exception:
        logger.exception("Email Versand fehlgeschlagen")


@app.route("/admin/newsletter")
def admin_newsletter():
    if not session.get("admin"):
        abort(403)

    subscribers = NewsletterSubscriber.query.order_by(
        NewsletterSubscriber.created_at.desc()
    ).all()

    return render_template(
        "admin_newsletter.html",
        subscribers=subscribers
    )


@app.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email")

    if not email:
        flash("Bitte gib eine gültige E-Mail-Adresse ein.", "error")
        return redirect("/")

    # Prüfen ob schon vorhanden
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        flash("Du bist bereits angemeldet.", "info")
        return redirect("/")

    # Token erzeugen
    token = str(uuid.uuid4())

    subscriber = NewsletterSubscriber(
        email=email,
        token=token,
        confirmed=False
    )

    db.session.add(subscriber)
    db.session.commit()

    # Bestätigungslink
    confirm_url = url_for("confirm_newsletter", token=token, _external=True)
    # HTML-Mail
    html_body = f"""
    <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
        <h2>Newsletter bestätigen</h2>
        <p>Danke für deine Anmeldung!</p>
        <p>Klicke auf den Button, um deine E-Mail zu bestätigen:</p>

        <a href="{confirm_url}" 
           style="
               display: inline-block;
               padding: 12px 20px;
               background-color: #7393B3;
               color: white;
               text-decoration: none;
               border-radius: 6px;
               font-weight: bold;
           ">
           Jetzt bestätigen
        </a>
    </div>
    """

    send_email(
        subject="Bitte bestätige deine Newsletter-Anmeldung",
        recipient=email,
        html=html_body
    )

    flash("Bitte bestätige deine Anmeldung per E-Mail.", "success")
    return redirect("/newsletterbesteatigung")


@app.route("/newsletter/confirm/<token>")
def confirm_newsletter(token):
    subscriber = NewsletterSubscriber.query.filter_by(token=token).first()

    if not subscriber:
        flash("Ungültiger Bestätigungslink.", "error")
        return redirect("/")

    subscriber.confirmed = True
    subscriber.token = None
    db.session.commit()

    flash("Newsletter erfolgreich bestätigt 🎉", "success")
    return redirect("/danke")


@app.route("/admin/send-newsletter", methods=["POST"])
def send_newsletter():
    if not session.get("admin"):
        abort(403)

    subject = request.form.get("subject")
    content = request.form.get("content")  # HTML erlaubt

    subscribers = NewsletterSubscriber.query.filter_by(confirmed=True).all()

    for sub in subscribers:
        unsubscribe_url = url_for(
            "unsubscribe_newsletter",
            token=sub.token,
            _external=True
        )

        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            {content}

            <p style="margin-top:20px; font-size:12px; color: gray;">
                <a href="{unsubscribe_url}">Abmelden vom Newsletter</a>
            </p>
        </div>
        """

        send_email(
            subject=subject,
            recipient=sub.email,
            html=html_body
        )

    return f"{len(subscribers)} Emails gesendet ✅"


@app.route("/newsletter/unsubscribe/<token>")
def unsubscribe_newsletter(token):
    subscriber = NewsletterSubscriber.query.filter_by(token=token).first()

    if not subscriber:
        flash("Ungültiger Abmeldelink.", "error")
        return redirect("/")

    db.session.delete(subscriber)
    db.session.commit()

    flash("Du hast dich erfolgreich vom Newsletter abgemeldet.", "success")
    return redirect("/")
# ============================
# RECHTLICHES
# ============================

@app.route("/agb")
def agb():
    return render_template("agb.html", user_email=session.get("user_email"))

@app.route("/datenschutz")
def datenschutz():
    return render_template("datenschutz.html", user_email=session.get("user_email"))

@app.route("/impressum")
def impressum():
    return render_template("impressum.html", user_email=session.get("user_email"))



# ============================
# DANKE SEITEN
# ============================

@app.route("/danke")
def danke():
    return render_template("danke.html", user_email=session.get("user_email"))

@app.route("/kontaktdanke")
def kontaktdanke():
    return render_template("kontaktdanke.html", user_email=session.get("user_email"))

@app.route("/bestelldanke")
def bestelldanke():
    return render_template("bestelldanke.html", user_email=session.get("user_email"))

@app.route("/newsletterbesteatigung")
def newsletterbesteatigung():
    return render_template("newsletterbesteatigung.html", user_email=session.get("user_email"))
    
@app.route("/newsletteranmeldung")
def newsletteranmeldung():
    return render_template("newsletteranmeldung.html", user_email=session.get("user_email"))
    
# ============================
# INDEX HAUPTSEITE
# ============================

@app.route("/")
def index():

    kategorienamen = [
        "Jacominus Gainsborough", "Mut oder Angst?!",
        "Klassiker", "Monstergeschichten",
        "Wichtige Fragen", "Weihnachten",
        "Kinder und Gefühle", "Dazugehören"
    ]

    kategorie_beschreibungen = {
        "Jacominus Gainsborough": {
            "kurz": "Einer, der sich erinnert. Und manchmal auch vergisst.",
            "lang": "Jacominus sitzt im Garten, denkt nach, lauscht dem Wind. Eine Erinnerung streift ihn – kaum greifbar, wie ein Traum, der sich beim Aufwachen auflöst. Und doch ist da etwas, das bleibt: ein Gefühl, warm und vertraut. Es sind die winzig kleinen Sekunden, die zählen. Die kaum sichtbaren Augenblicke zwischen zwei Herzschlägen, in denen sich alles entscheiden kann. Ein Blick. Ein Lächeln. Ein Wiedersehen. Und irgendwo ist immer jemand unterwegs. Über Wiesen, durch Straßen, vorbei an flüchtigen Begegnungen. Schritt für Schritt, einer Verabredung entgegen. Vielleicht Punkt zwölf. Vielleicht genau im richtigen Moment. So entfaltet sich ein Leben – nicht laut und in Bildern und Worten, die bleiben. In Begegnungen, die alles verändern können. Kein außergewöhnliches Leben. Und doch ein ganz besonderes. Das Leben von Jacominus Gainsborough"
        }
    }

    kategorien = [
        (k, [p for p in produkte if p.get("kategorie") == k])
        for k in kategorienamen
    ]

    return render_template(
        "index.html",
        kategorien=kategorien,
        kategorie_beschreibungen=kategorie_beschreibungen,
        user_email=session.get("user_email")
    )

# =====================================================
# START (RENDER READY)
# =====================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
