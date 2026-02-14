from flask import Flask, render_template, request, redirect, flash, abort, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import json
import logging
import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import secrets
from datetime import datetime
import base64
from moluna_mapper import build_moluna_payload
from moluna_client import send_order_to_moluna

# -------------------------------------------------
# SETUP
# -------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------------------------------
# MODELS
# -------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Bestellung(db.Model):
    __tablename__ = "bestellungen"

    id = db.Column(db.Integer, primary_key=True)

    mol_kunde_id = db.Column(db.Integer)
    rechnungsadresse_id = db.Column(db.Integer)
    mol_zahlart_id = db.Column(db.Integer)
    mol_verkaufskanal_id = db.Column(db.Integer)

    bestelldatum = db.Column(db.String(50))
    bestellreferenz = db.Column(db.String(100))
    seite = db.Column(db.String(200))
    bestellfreigabe = db.Column(db.Integer)

    liefer_anrede = db.Column(db.String(50))
    liefer_vorname = db.Column(db.String(100))
    liefer_nachname = db.Column(db.String(100))
    liefer_strasse = db.Column(db.String(200))
    liefer_hausnummer = db.Column(db.String(50))
    liefer_plz = db.Column(db.String(20))
    liefer_ort = db.Column(db.String(100))
    liefer_land = db.Column(db.String(100))
    liefer_land_iso = db.Column(db.String(10))
    liefer_tel = db.Column(db.String(50))

    status = db.Column(db.String(50), default="neu")
    moluna_status = db.Column(db.String(50))
    trackingnummer = db.Column(db.String(100))
    versanddienstleister = db.Column(db.String(100))
    versanddatum = db.Column(db.String(50))

    positionen = db.relationship("BestellPosition", backref="bestellung", cascade="all, delete-orphan")
    zusatz = db.relationship("BestellZusatz", backref="bestellung", cascade="all, delete-orphan")


class BestellPosition(db.Model):
    __tablename__ = "bestell_positionen"

    id = db.Column(db.Integer, primary_key=True)
    bestell_id = db.Column(db.Integer, db.ForeignKey("bestellungen.id"), nullable=False)

    ean = db.Column(db.String(20))
    bezeichnung = db.Column(db.String(500))
    menge = db.Column(db.Integer)
    ek_netto = db.Column(db.Float)
    vk_brutto = db.Column(db.Float)
    referenz = db.Column(db.String(200))


class BestellZusatz(db.Model):
    __tablename__ = "bestell_zusatz"

    id = db.Column(db.Integer, primary_key=True)
    bestell_id = db.Column(db.Integer, db.ForeignKey("bestellungen.id"), nullable=False)

    typ = db.Column(db.String(100))
    value = db.Column(db.String(200))


class StornoToken(db.Model):
    __tablename__ = "storno_tokens"

    id = db.Column(db.Integer, primary_key=True)
    bestell_id = db.Column(db.Integer, db.ForeignKey("bestellungen.id"), nullable=False)
    token = db.Column(db.String(200), nullable=False)
    created = db.Column(db.String(50))


with app.app_context():
    db.create_all()

# -------------------------------------------------
# BESTELLUNG ERSTELLEN
# -------------------------------------------------

@app.route("/bestellung", methods=["POST"])
def neue_bestellung():
    try:
        data = request.get_json() or {}
        liefer = data.get("lieferadresse", {})

        bestellung = Bestellung(
            mol_kunde_id=data.get("mol_kunde_id"),
            bestelldatum=data.get("bestelldatum"),
            bestellreferenz=data.get("bestellreferenz"),
            mol_verkaufskanal_id=data.get("mol_verkaufskanal_id"),

            liefer_anrede=liefer.get("anrede"),
            liefer_vorname=liefer.get("vorname"),
            liefer_nachname=liefer.get("nachname"),
            liefer_strasse=liefer.get("strasse"),
            liefer_hausnummer=liefer.get("hausnummer"),
            liefer_plz=liefer.get("plz"),
            liefer_ort=liefer.get("ort"),
            liefer_land=liefer.get("land"),
        )

        db.session.add(bestellung)
        db.session.flush()

        for pos in data.get("auftrag_position", []):
            db.session.add(BestellPosition(
                bestell_id=bestellung.id,
                ean=pos.get("ean"),
                bezeichnung=pos.get("pos_bezeichnung"),
                menge=int(pos.get("menge", 0)),
                ek_netto=float(pos.get("ek_netto", 0)),
                vk_brutto=float(pos.get("vk_brutto", 0)),
            ))

        db.session.commit()

        return jsonify({"success": True, "bestellId": bestellung.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------------------------------
# CRUD ROUTES
# -------------------------------------------------

@app.route("/bestellungen")
def alle_bestellungen():
    bestellungen = Bestellung.query.all()
    return jsonify([
        {
            "id": b.id,
            "status": b.status,
            "bestellreferenz": b.bestellreferenz,
            "bestelldatum": b.bestelldatum
        } for b in bestellungen
    ])


@app.route("/bestellung/<int:bestell_id>")
def bestellung_detail(bestell_id):
    b = Bestellung.query.get(bestell_id)
    if not b:
        return jsonify({"error": "Nicht gefunden"}), 404

    return jsonify({
        "bestellung": {
            "id": b.id,
            "status": b.status,
            "trackingnummer": b.trackingnummer
        },
        "positionen": [
            {"ean": p.ean, "menge": p.menge}
            for p in b.positionen
        ]
    })


@app.route("/bestellung/<int:bestell_id>", methods=["DELETE"])
def bestellung_loeschen(bestell_id):
    b = Bestellung.query.get(bestell_id)
    if not b:
        return jsonify({"error": "Nicht gefunden"}), 404

    db.session.delete(b)
    db.session.commit()
    return jsonify({"success": True})

# -------------------------------------------------
# MOLUNA
# -------------------------------------------------

def lade_bestellung(bestell_id):
    b = Bestellung.query.get(bestell_id)
    if not b:
        return None

    return {
        "bestellung": {"id": b.id},
        "positionen": [{"ean": p.ean, "menge": p.menge} for p in b.positionen]
    }


TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

def send_bestellung_an_moluna(bestell_id):
    order = lade_bestellung(bestell_id)
    if not order:
        raise Exception("Bestellung nicht gefunden")

    payload = build_moluna_payload(order)

    if TEST_MODE:
        print("TEST MODE – Bestellung wird NICHT gesendet")
        return payload

    return send_order_to_moluna(payload)
# -------------------------------------------------
# STATUS UPDATE (NEU)
# -------------------------------------------------

@app.route("/bestellung/<int:bestell_id>/status", methods=["POST"])
def update_status(bestell_id):
    b = Bestellung.query.get(bestell_id)
    if not b:
        return jsonify({"error": "Nicht gefunden"}), 404

    data = request.get_json() or {}
    b.status = data.get("status", b.status)
    b.trackingnummer = data.get("trackingnummer", b.trackingnummer)
    b.versanddienstleister = data.get("versanddienstleister", b.versanddienstleister)
    b.versanddatum = datetime.now().isoformat()

    db.session.commit()

    return jsonify({"success": True})

# -------------------------------------------------
# START
# -------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
