

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Gutschein(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(50), unique=True)
    wert = db.Column(db.Float)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    eingelöst = db.Column(db.Boolean, default=False)

# ----------------------
# User Modell
# ----------------------




class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    punkte = db.Column(db.Integer, default=0)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----------------------
# Bestell-Modelle
# ----------------------

class Bestellung(db.Model):
    __tablename__ = "bestellungen"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)

    collectkey = db.Column(db.String(100))   


    # ⭐ PERSONENDATEN
    vorname = db.Column(db.String(120))
    nachname = db.Column(db.String(120))
    strasse = db.Column(db.String(200))
    hausnummer = db.Column(db.String(20))
    plz = db.Column(db.String(20))
    stadt = db.Column(db.String(120))
    land = db.Column(db.String(120))
    adresszusatz =  db.Column(db.String(120))
    telefon = db.Column(db.String(50))
    paymentmethod = db.Column(db.String(50))

       # ⭐ MOLUNA-FELDER
    moluna_status = db.Column(db.String(50))         # Status der Bestellung bei Moluna
    moluna_order_id = db.Column(db.String(100))      # Moluna Order-ID
    trackingnummer = db.Column(db.String(100))       # Trackingnummer
    logistiker = db.Column(db.String(200))          # Logistiker z.B. DHL, kommagetrennt
    paketart = db.Column(db.String(200))            # z.B. Paket, Grossbrief, kommagetrennt
    eans = db.Column(db.String(500))       

    bestelldatum = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    positionen = db.relationship(
        "BestellPosition",
        backref="bestellung",
        cascade="all, delete-orphan"
    )

class BestellPosition(db.Model):
    __tablename__ = "bestellpositionen"

    id = db.Column(db.Integer, primary_key=True)
    bestellung_id = db.Column(db.Integer, db.ForeignKey("bestellungen.id"))
    ean = db.Column(db.String(50))
    bezeichnung = db.Column(db.String(200))
    menge = db.Column(db.Integer)
    preis = db.Column(db.Float)




# ----------------------
# Produkt Modell (Hybrid-System)
# ----------------------

class Produkt(db.Model):
    __tablename__ = "produkte"

    id = db.Column(db.Integer, primary_key=True)

    ean = db.Column(db.String(50), unique=True, nullable=False)

    name = db.Column(db.String(255))
    autor = db.Column(db.String(255))
    beschreibung = db.Column(db.Text)

    preis = db.Column(db.Float)
    kategorie = db.Column(db.String(120))

    lagerbestand = db.Column(db.Integer)

    bild_url = db.Column(db.String(500))

    zuletzt_aktualisiert = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Produkt {self.name}>"
