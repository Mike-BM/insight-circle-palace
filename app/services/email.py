import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_content: str):
    resend_api_key = os.environ.get("RESEND_API_KEY")
    if resend_api_key:
        try:
            import resend

            resend.api_key = resend_api_key
            from_email = os.environ.get(
                "EMAIL_FROM", "Insight Circle <onboarding@resend.dev>"
            )
            reply_to = os.environ.get("EMAIL_REPLY_TO", "Insightcirclepalace@gmail.com")

            params = {
                "from": from_email,
                "to": [to_email.lower().strip()],
                "subject": subject,
                "html": html_content,
            }
            if reply_to:
                params["reply_to"] = reply_to

            response = resend.Emails.send(params)
            print(
                f"Email successfully sent to {to_email} via Resend. ID: {response.get('id') if isinstance(response, dict) else response}"
            )
            return response
        except Exception as e:
            print(f"Failed to send email via Resend: {e}")
            logger.error(f"Failed to send email via Resend to {to_email}: {e}")

    # Fallback to SMTP if SMTP credentials are provided
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        print(
            "No email credentials configured (Neither RESEND_API_KEY nor SMTP_USER/SMTP_PASSWORD). Skipping email send."
        )
        return None

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=5)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Email successfully sent to {to_email} via SMTP")
        return True
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}")
        logger.error(f"Failed to send email via SMTP to {to_email}: {e}")
        return None
