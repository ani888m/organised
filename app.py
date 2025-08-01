from flask import Flask, render_template, request
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)






@app.route('/')

def index():
    return render_template('index.html')
    
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

if __name__ == '__main__':
    app.run(debug=True)
