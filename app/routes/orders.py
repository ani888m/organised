from flask import Blueprint, request, jsonify
from ..services.orders import save_order, get_order, get_all_orders, delete_order, generate_cancel_token
from services.mail import send_email
from services.buchbutler import lade_rechnung
import logging

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__)


# ----------------------------
# Neue Bestellung
# ----------------------------
@orders_bp.route("/bestellung", methods=["POST"])
def neue_bestellung():
    data = request.get_json() or {}
    email = data.get("email")

    try:
        # Bestellung speichern
        bestell_id = save_order(data)

        # Stornotoken erzeugen
        token = None
        if email:
            token = generate_cancel_token(bestell_id)
            cancel_link = f"https://deinedomain.de/storno/{token}"

            # Rechnung laden
            pdf_bytes = None
            if data.get("rechnungsdatei"):
                pdf_bytes = lade_rechnung(data["rechnungsdatei"])

            # E-Mail versenden
            try:
                send_email(
                    subject="Ihre Bestellung",
                    body=f"""Vielen Dank für Ihre Bestellung!\n\nBestellnummer: {bestell_id}\n\nStornieren Sie hier:\n{cancel_link}""",
                    recipient=email,
                    pdf_bytes=pdf_bytes
                )
            except Exception as e:
                logger.error(f"Bestellmail Fehler: {e}")

        return jsonify({"success": True, "bestellId": bestell_id, "stornoToken": token})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------
# Alle Bestellungen
# ----------------------------
@orders_bp.route("/bestellungen", methods=["GET"])
def alle_bestellungen():
    orders = get_all_orders()
    return jsonify(orders)


# ----------------------------
# Bestellung Detail inkl Positionen + Zusatz
# ----------------------------
@orders_bp.route("/bestellung/<int:bestell_id>", methods=["GET"])
def bestellung_detail(bestell_id):
    order = get_order(bestell_id)
    if not order:
        return jsonify({"error": "Nicht gefunden"}), 404
    return jsonify(order)


# ----------------------------
# Bestellung löschen
# ----------------------------
@orders_bp.route("/bestellung/<int:bestell_id>", methods=["DELETE"])
def bestellung_loeschen(bestell_id):
    delete_order(bestell_id)
    return jsonify({"success": True})
