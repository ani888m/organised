




from datetime import datetime
from flask import request, redirect, flash, url_for
from flask_mail import Message

from models import db, NewsletterSubscriber



from utils import generate_token  # falls ausgelagert


from flask import Blueprint

from flask import current_app

newsletter_bp = Blueprint("newsletter", __name__)


# ============================
# NEWSLETTER
# ============================

@newsletter_bp.route("/newsletter", methods=["POST"])
def newsletter():
  

    email = request.form.get("email")

    if not email:
        flash("Bitte gültige E-Mail eingeben", "error")
        return redirect("/")

    existing = NewsletterSubscriber.query.filter_by(email=email).first()

    if existing:
        flash("E-Mail bereits registriert", "info")
        return redirect("/")

    confirm_token = generate_token()
    unsubscribe_token = generate_token()

    subscriber = NewsletterSubscriber(
        email=email,
        confirm_token=confirm_token,
        unsubscribe_token=unsubscribe_token
    )

    db.session.add(subscriber)
    db.session.commit()

    confirm_link = url_for("confirm_newsletter", token=confirm_token, _external=True)

    send_email(
        subject="Bitte bestätige deine Anmeldung",
        recipient=email,
        body=f"""
Hallo 👋

bitte bestätige deine Newsletter-Anmeldung:

{confirm_link}

Falls du dich NICHT angemeldet hast, ignoriere diese Mail einfach.
"""
    )

    flash("Bitte bestätige deine E-Mail (Posteingang prüfen)", "success")
    return redirect("/danke")

#  Bestätigungs-Route (Double Opt-in)

@newsletter_bp.route("/confirm/<token>")
def confirm_newsletter(token):
    subscriber = NewsletterSubscriber.query.filter_by(confirm_token=token).first()

    if not subscriber:
        return "Ungültiger Bestätigungslink", 404

    if subscriber.is_active:
        return "Bereits bestätigt ✅"

    subscriber.is_active = True
    subscriber.confirmed_at = datetime.utcnow()
    db.session.commit()

    return "Danke! Deine Anmeldung ist bestätigt 🎉"

# NEWSLETTER abmelder

@newsletter_bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    subscriber = NewsletterSubscriber.query.filter_by(unsubscribe_token=token).first()

    if not subscriber:
        return "Ungültiger Link", 404

    subscriber.is_active = False
    db.session.commit()

    return "Du wurdest erfolgreich abgemeldet."


#newsletter senden

def send_newsletter(subject, content):
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True).all()

    for sub in subscribers:
        unsubscribe_link = url_for("unsubscribe", token=sub.unsubscribe_token, _external=True)

        full_content = f"""
{content}

---
Abmelden:
{unsubscribe_link}
"""

        send_email(
            subject=subject,
            recipient=sub.email,
            body=full_content
        )


def send_email(subject, recipient, body):
    from flask_mail import Message
    msg = Message(subject, recipients=[recipient])

    msg.body = body
    msg.html = f"""
    <html>
      <body style="font-family:Arial;">
        <p>{body.replace('\n', '<br>')}</p>

        <hr>
        <p style="font-size:12px;color:gray;">
          Du erhältst diese Mail, weil du dich angemeldet hast.<br>
        </p>
      </body>
    </html>
    """

    mail.send(msg)
