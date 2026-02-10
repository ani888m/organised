import os
import logging
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")


def send_email(subject, body, recipient=None, pdf_bytes=None, pdf_name="Rechnung.pdf"):
    """
    Sendet eine E-Mail über SendGrid.
    
    :param subject: Betreff
    :param body: Plain-Text Nachricht
    :param recipient: Empfänger, Standard ist EMAIL_SENDER
    :param pdf_bytes: optional, PDF Bytes zum Anhängen
    :param pdf_name: Dateiname für PDF
    """
    if not recipient:
        recipient = EMAIL_SENDER

    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body
    )

    # PDF anhängen, falls vorhanden
    if pdf_bytes:
        try:
            encoded_file = base64.b64encode(pdf_bytes).decode()
            attachment = Attachment(
                FileContent(encoded_file),
                FileName(pdf_name),
                FileType("application/pdf"),
                Disposition("attachment")
            )
            message.attachment = attachment
        except Exception as e:
            logger.error(f"PDF konnte nicht angehängt werden: {e}")

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"E-Mail erfolgreich gesendet an {recipient}")
        return True
    except Exception as e:
        logger.error(f"E-Mail Fehler an {recipient}: {e}")
        return False
