import os
from dotenv import load_dotenv
# ... andere Imports wie Flask, db, mail etc.

# Laden der Umgebungsvariablen am Anfang der Datei
load_dotenv()

# Suchen und Initialisieren des SendGrid API Keys
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
if not SENDGRID_API_KEY:
    print("FATAL ERROR: SENDGRID_API_KEY ist nicht in den Umgebungsvariablen gesetzt!")
    # Optional: Flask-Anwendung stoppen oder Fehlermeldung anzeigen

# Ihre vorhandene newsletter_signup-Route
@app.route('/newsletter', methods=['POST'])
def newsletter_signup():
    email = request.form.get('email')
    
    # 1. Prüfen, ob der API-Schlüssel verfügbar ist
    if not SENDGRID_API_KEY:
        print("FEHLER: Newsletter-Versand nicht möglich, da SENDGRID_API_KEY fehlt.")
        flash('Newsletter-Anmeldung fehlgeschlagen. Bitte versuchen Sie es später erneut.', 'error')
        return redirect(url_for('index'))

    # 2. Datenbankprüfung (Ihr vorhandener Code hier)
    # ...

    try:
        # Ihre SendGrid-Message-Konfiguration
        message = Mail(
            from_email=('ihre-website-email@example.com', 'Ihr Buchverlag'), # MUSS eine von SendGrid verifizierte E-Mail sein
            to_emails=email,
            subject='Ihre Newsletter-Anmeldung beim Buchverlag',
            html_content='<strong>Vielen Dank für Ihre Anmeldung!</strong> Wir halten Sie auf dem Laufenden.'
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        # Erfolgreiches Logging: Statuscode von SendGrid
        print(f"Newsletter-Bestätigung erfolgreich gesendet. SendGrid Status: {response.status_code}")
        
        # Optional: Zusätzliche Debug-Informationen
        if response.status_code != 202 and response.status_code != 200:
            print(f"WARNUNG: SendGrid Body (bei unerwartetem Status): {response.body}")
            
        flash('Vielen Dank! Ihre Newsletter-Anmeldung war erfolgreich.', 'success')

    except Exception as e:
        # Kritisches Fehler-Logging: Zeigt den tatsächlichen Fehler im Render Log
        print(f"KRITISCHER FEHLER beim Senden der Newsletter-E-Mail: {e}")
        # Wenn der Fehler von SendGrid selbst kommt, enthält er oft nützliche Details
        if hasattr(e, 'response') and e.response is not None:
             print(f"SendGrid API Fehler: Status {e.response.status_code}, Body: {e.response.body}")
             
        flash('Newsletter-Anmeldung fehlgeschlagen. Bitte versuchen Sie es später erneut.', 'error')

    return redirect(url_for('index'))
