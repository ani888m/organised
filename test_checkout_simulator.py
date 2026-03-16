
import json

# --- Simulationsfunktionen ---
def lade_testprodukt(json_path="test_product.json"):
    """Lädt ein Testprodukt aus JSON."""
    with open(json_path, "r") as f:
        return [json.load(f)]  # Liste für Warenkorb

def sync_cart(cart_items):
    """Simuliert das Synchronisieren des Warenkorbs."""
    print("SYNCED CART:", cart_items)
    return True  # simuliert erfolgreichen Sync

def start_checkout(cart_items):
    """Simuliert den Checkout-Prozess."""
    if not cart_items:
        print("Warenkorb leer. Checkout abgebrochen.")
        return False

    print("Checkout gestartet für folgende Produkte:")
    for item in cart_items:
        print(f"- {item['title']} | Preis: {item['price']} | Menge: {item['quantity']} | EAN: {item['ean']}")
    
    print("Kundendaten für PayPal gespeichert (simuliert).")
    return True

def create_paypal_order(cart_items):
    """Simuliert die Erstellung einer PayPal-Bestellung."""
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    print(f"PayPal-Bestellung erstellt. Gesamtbetrag: {total} EUR (simuliert)")
    return {"order_id": "TEST123456"}

def capture_paypal_order(order_id):
    """Simuliert das Abschließen der PayPal-Zahlung."""
    print(f"PayPal-Bestellung {order_id} erfolgreich abgeschlossen (simuliert).")
    return True

def sende_bestellung_an_buchbutler(cart_items):
    """Simuliert den Versand an Buchbutler (nur Logging)."""
    print("Buchbutler-Bestellung gesendet (simuliert):")
    for item in cart_items:
        print(f"- {item['title']} | EAN: {item['ean']} | Menge: {item['quantity']}")
    return True

# --- Main Simulation ---
if __name__ == "__main__":
    # 1️⃣ Testprodukt laden
    cart_items = lade_testprodukt("test_product.json")

    # 2️⃣ Warenkorb synchronisieren
    if sync_cart(cart_items):
        # 3️⃣ Checkout starten
        if start_checkout(cart_items):
            # 4️⃣ PayPal-Bestellung erstellen
            paypal_order = create_paypal_order(cart_items)
            
            # 5️⃣ PayPal-Bestellung abschließen
            if capture_paypal_order(paypal_order["order_id"]):
                # 6️⃣ Bestellung an Buchbutler senden (simuliert)
                sende_bestellung_an_buchbutler(cart_items)

    print("\nSimulation abgeschlossen. Keine echte Bestellung wurde gesendet.")
