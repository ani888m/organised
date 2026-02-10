from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# --------------------------------
# User Modell
# --------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"


# --------------------------------
# Beispiel für zukünftige Modelle
# --------------------------------
# Du könntest hier später auch Bestellungen, Produkte etc. mit SQLAlchemy abbilden
# Für jetzt nutzen wir die SQLite-Bestell-DB noch direkt über Services/orders.py

# class Bestellung(db.Model):
#     __tablename__ = "bestellungen"
#     id = db.Column(db.Integer, primary_key=True)
#     ...
