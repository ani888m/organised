from flask import Flask, render_template, request, redirect, flash
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'irgendetwasgeheimes'  # wichtig für Flash-Messages


# Startseite
@app.route('/')
def index():
    return render_template('index.html')

# Unterseiten
@app.route('/navbar')
def navbar():
    return render_template('navbar.html')

@app.route('/team')
def team():
    return render_template('Team.html')

@app.route('/vision')
def vision():
    return render_template('vision.html')

@app.route('/presse')
def presse():
    return render_template('presse.html')

@app.route('/kontakt')
def kontakt():
    return render_template('kontakt.html')

@app.route("/newsletter-snippet")
def newsletter_snippet():
    return render_template("newsletter.html")


# 📬 Kontaktformular-Submit
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    send_email(name, email, message)

    return "Danke! Deine Nachricht wurde gesendet."


def send_email(name, email, message):
    sender = 'antonyan125@gmail.com'
    app_password = 'ffutcvkflhcgiijl'
    recipient = 'antonyan125@gmail.com'

    subject = f'Neue Nachricht von {name}'
    body = f"Von: {name} <{email}>\n\nNachricht:\n{message}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print("E-Mail gesendet!")
    except Exception as e:
        print("Fehler beim Senden:", e)


# 📨 Newsletter-Submit (nur E-Mail-Benachrichtigung)
@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email')

    if not email:
        flash('Bitte gib eine gültige E-Mail-Adresse ein.', 'error')
        return redirect('/')

    try:
        send_newsletter_email(email)
        flash('Danke für deine Anmeldung zum Newsletter!', 'success')
    except Exception as e:
        print("Fehler beim Newsletter-Versand:", e)
        flash('Es gab ein Problem bei der Anmeldung.', 'error')

    return redirect('/')


def send_newsletter_email(email):
    sender = 'antonyan125@gmail.com'
    app_password = 'ffutcvkflhcgiijl'
    recipient = 'antonyan125@gmail.com'

    subject = 'Neue Newsletter-Anmeldung'
    body = f'Neue Newsletter-Anmeldung:\n\n{email}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print("Newsletter-Benachrichtigung gesendet!")
    except Exception as e:
        print("Fehler beim Senden der Newsletter-Benachrichtigung:", e)


# 🔁 App starten
if __name__ == '__main__':
    app.run(debug=True)
