from flask import Flask
from models import db
from routes.shop import shop_bp
from routes.orders import orders_bp



# -----------------------------
# Flask App erstellen
# -----------------------------
app = Flask(__name__)
app.secret_key = "DEIN_SECRET_KEY"

# -----------------------------
# SQLAlchemy konfigurieren
# -----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Tabellen erstellen
with app.app_context():
    db.create_all()

# -----------------------------
# Blueprints registrieren
# -----------------------------
app.register_blueprint(shop_bp)
app.register_blueprint(orders_bp)

# -----------------------------
# Optional: Cron oder andere einfache Routen
# -----------------------------
@app.route("/cron")
def cron():
    print("Cronjob wurde ausgelöst")
    return "OK"

# -----------------------------
# App starten
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
