import uuid


def build_moluna_payload(order, moluna_user, moluna_pass):

    # collectkey generieren (Moluna Pflichtfeld)
    collectkey = str(uuid.uuid4())

    payload = {
        "username": moluna_user,
        "passwort": moluna_pass,

        "auftrag_kopf": {
            "mol_kunde_id": order["bestellung"]["mol_kunde_id"],
            "rechnungsadresse_id": order["bestellung"]["rechnungsadresse_id"],
            "mol_zahlart_id": order["bestellung"]["mol_zahlart_id"],
            "bestelldatum": order["bestellung"]["bestelldatum"],
            "bestellreferenz": order["bestellung"]["bestellreferenz"],
            "seite": order["bestellung"]["seite"],
            "bestellfreigabe": order["bestellung"]["bestellfreigabe"],
            "mol_verkaufskanal_id": order["bestellung"]["mol_verkaufskanal_id"]
        },

        "lieferadresse": {
            "anrede": order["bestellung"]["liefer_anrede"],
            "vorname": order["bestellung"]["liefer_vorname"],
            "nachname": order["bestellung"]["liefer_nachname"],
            "zusatz": order["bestellung"]["liefer_zusatz"],
            "strasse": order["bestellung"]["liefer_strasse"],
            "hausnummer": order["bestellung"]["liefer_hausnummer"],
            "adresszeile_1": order["bestellung"]["liefer_adresszeile1"],
            "adresszeile_2": order["bestellung"]["liefer_adresszeile2"],
            "adresszeile_3": order["bestellung"]["liefer_adresszeile3"],
            "plz": order["bestellung"]["liefer_plz"],
            "ort": order["bestellung"]["liefer_ort"],
            "land_iso": order["bestellung"]["liefer_land_iso"],
            "tel": order["bestellung"]["liefer_tel"]
        },

        "auftrag_position": [],

        "auftrag_zusatz": [
            {
                "typ": "collectkey",
                "value": collectkey
            }
        ]
    }

    # Positionen hinzufügen
    for pos in order["positionen"]:

        referenz = pos["referenz"]
        if not referenz:
            referenz = f"{pos['bestell_id']}-{pos['id']}"

        payload["auftrag_position"].append({
            "ean": pos["ean"],
            "pos_bezeichnung": pos["bezeichnung"],
            "menge": int(pos["menge"]),
            "ek_netto": float(pos["ek_netto"]),
            "vk_brutto": float(pos["vk_brutto"]),
            "pos_referenz": referenz
        })

    return payload
