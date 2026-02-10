import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BUCHBUTLER_USER = os.getenv("BUCHBUTLER_USER")
BUCHBUTLER_PASSWORD = os.getenv("BUCHBUTLER_PASSWORD")

BASE_URL = "https://api.buchbutler.de"


# --------------------------------
# Helper
# --------------------------------
def check_auth():
    if not BUCHBUTLER_USER or not BUCHBUTLER_PASSWORD:
        logger.error("Buchbutler Zugangsdaten fehlen")
        return False
    return True


def to_float(value):
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def to_int(value):
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def attr(attrs, key):
    return (attrs.get(key) or {}).get("Wert", "")


# --------------------------------
# Request Funktion
# --------------------------------
def buchbutler_request(endpoint, ean):

    if not check_auth():
        return None

    url = f"{BASE_URL}/{endpoint}/"

    params = {
        "username": BUCHBUTLER_USER,
        "passwort": BUCHBUTLER_PASSWORD,
        "ean": ean
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data or "response" not in data:
            return None

        return data["response"]

    except Exception:
        logger.exception("Buchbutler API Fehler")
        return None


# --------------------------------
# CONTENT API
# --------------------------------
def lade_produkt_von_api(ean):

    res = buchbutler_request("CONTENT", ean)

    if not res:
        return None

    attrs = res.get("Artikelattribute") or {}

    return {
        "id": to_int(res.get("pim_artikel_id")),
        "name": res.get("bezeichnung"),
        "autor": attr(attrs, "Autor"),
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


# --------------------------------
# MOVEMENT API
# --------------------------------
def lade_bestand_von_api(ean):

    res = buchbutler_request("MOVEMENT", ean)

    if not res:
        return None

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


# --------------------------------
# Rechnung laden
# --------------------------------
def lade_rechnung(dateiname):

    url = f"https://api.buchbutler.de/RECHNUNG/{dateiname}"

    try:
        response = requests.get(
            url,
            auth=(BUCHBUTLER_USER, BUCHBUTLER_PASSWORD)
        )

        if response.status_code == 200:
            return response.content

    except Exception:
        logger.exception("Rechnung konnte nicht geladen werden")

    return None
