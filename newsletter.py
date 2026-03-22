from flask import Blueprint, request, redirect, flash, url_for
from datetime import datetime
import secrets

from app import db, mail
from models import NewsletterSubscriber
from flask_mail import Message

newsletter_bp = Blueprint("newsletter", __name__)

def generate_token():
    return secrets.token_urlsafe(32)

@newsletter_bp.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email")
    if not email:
        flash("Bitte gültige E-Mail eingeben", "error")
        return redirect("/")

    if NewsletterSubscriber.query.filter_by(email=email).first():
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

    confirm_link = url_for("newsletter.confirm_newsletter", token=confirm_token, _external=True)

    send_email(
        subject="Bitte bestätige deine Anmeldung",
        recipient=email,
        body=f"Bitte bestätige hier: {confirm_link}"
    )

    flash("Bitte bestätige deine E-Mail (Posteingang prüfen)", "success")
    return redirect("/danke")


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


@newsletter_bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    subscriber = NewsletterSubscriber.query.filter_by(unsubscribe_token=token).first()
    if not subscriber:
        return "Ungültiger Link", 404

    subscriber.is_active = False
    db.session.commit()
    return "Du wurdest erfolgreich abgemeldet."


def send_newsletter(subject, content):
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True).all()
    for sub in subscribers:
        unsubscribe_link = url_for("newsletter.unsubscribe", token=sub.unsubscribe_token, _external=True)
        full_content = f"{content}\n\n---\nAbmelden: {unsubscribe_link}"
        send_email(subject, sub.email, full_content)


def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    msg.html = f"<p>{body.replace(chr(10), '<br>')}</p><hr><p style='font-size:12px;color:gray;'>Du erhältst diese Mail, weil du dich angemeldet hast.</p>"
    mail.send(msg)
