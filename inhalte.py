from kategorien import kategorie_beschreibungen

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
            "kurz": "Poetische Bilderbücher über das Leben und große Gefühle.",
            "lang": "Diese Werke erzählen von Erinnerungen, Verlust, Liebe und Neubeginn. Kunstvoll illustriert und tief berührend – für Kinder und Erwachsene."
        },
        "Klassiker": {
            "kurz": "Zeitlose Kinderbuchklassiker für jede Generation.",
            "lang": "Diese Bücher haben Generationen geprägt und begeistern noch heute durch ihre Geschichten, Illustrationen und Werte."
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
