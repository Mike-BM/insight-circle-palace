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
            from_email = os.environ.get("EMAIL_FROM")
            # If unset or still pointing to testing sandbox address on Vercel, upgrade to verified domain
            if not from_email or "resend.dev" in from_email.lower():
                from_email = "Insight Circle Palace <notifications@insightcirclepalace.com>"
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


import urllib.parse
from html import escape


def wrap_email_layout(title: str, content_html: str, base_url: str = "https://insightcirclepalace.com") -> str:
    clean_base = (base_url or "https://insightcirclepalace.com").rstrip("/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #050A15; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #cbd5e1; -webkit-font-smoothing: antialiased;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #050A15; padding: 40px 16px;">
        <tr>
            <td align="center">
                <!-- Email Container -->
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #0A1124; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 28px 32px; background: linear-gradient(180deg, #0e1832 0%, #0A1124 100%); border-bottom: 1px solid rgba(212, 163, 69, 0.2); text-align: center;">
                            <a href="{clean_base}" style="text-decoration: none; display: inline-block;">
                                <div style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">
                                    INSIGHT CIRCLE <span style="color: #D4A345;">PALACE</span>
                                </div>
                                <div style="font-size: 11px; color: #D4A345; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px;">
                                    Executive Community & Masterclasses
                                </div>
                            </a>
                        </td>
                    </tr>
                    <!-- Main Body -->
                    <tr>
                        <td style="padding: 32px 32px 24px 32px;">
                            {content_html}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; background-color: #060B18; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center; font-size: 12px; color: #64748b; line-height: 1.6;">
                            <p style="margin: 0 0 8px 0; color: #94a3b8;">
                                <strong>Insight Circle Palace</strong> • Flagship Masterclasses & Executive Leadership
                            </p>
                            <p style="margin: 0 0 12px 0;">
                                Weekly Insighters Monday masterclasses are 100% free and open to everyone.
                            </p>
                            <p style="margin: 0; font-size: 11px;">
                                <a href="{clean_base}/static/monday-registration.html" style="color: #D4A345; text-decoration: none; margin: 0 8px;">Upcoming Masterclass</a> |
                                <a href="{clean_base}/recordings" style="color: #D4A345; text-decoration: none; margin: 0 8px;">Recordings Archive</a> |
                                <a href="{clean_base}/static/join.html" style="color: #D4A345; text-decoration: none; margin: 0 8px;">Join Palace</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def make_google_calendar_url(title: str, details: str, location: str = "Online Google Meet / Zoom") -> str:
    params = {
        "action": "TEMPLATE",
        "text": title,
        "details": details,
        "location": location,
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"


def build_monday_registration_email(
    full_name: str,
    session_date: str,
    session_info: dict = None,
    base_url: str = "https://insightcirclepalace.com",
    is_resend: bool = False,
) -> str:
    session_info = session_info or {}
    clean_base = (base_url or "https://insightcirclepalace.com").rstrip("/")
    topic = session_info.get("banner_short_description") or "Insighters Monday Live Masterclass"
    desc = session_info.get("full_session_description") or "Weekly live interactive masterclass with industry leaders, founders, and subject matter experts."
    meeting_link = (session_info.get("meeting_link") or "").strip()
    poster_url = (session_info.get("poster_url") or "").strip()
    reg_page_url = f"{clean_base}/monday-registration"

    cal_title = f"Insighters Monday: {topic}"
    cal_desc = f"Masterclass: {topic}\n\nDate: {session_date}\n\nDescription: {desc}\n\nMeeting link: {meeting_link or 'Will be activated prior to start'}\n\nInsight Circle Palace: {clean_base}"
    cal_url = make_google_calendar_url(cal_title, cal_desc, location=meeting_link or "Online (Insight Circle Palace)")

    wa_text = f"*Insighters Monday Masterclass — Insight Circle Palace*\n\nI just registered for this week's live session:\n*Topic:* {topic}\n*Date:* {session_date}\n\n*100% Free & Open to Everyone!* Join here:\n{reg_page_url}"
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"

    greeting_headline = "Here are your confirmed session access details:" if is_resend else "Your seat is officially reserved & confirmed!"
    greeting_sub = "We are thrilled to have you join us for this week's flagship session." if not is_resend else "You requested a copy of your session links and registration details."

    meeting_box = ""
    if meeting_link:
        meeting_box = f"""
        <div style="background: rgba(212, 163, 69, 0.08); border: 1px solid rgba(212, 163, 69, 0.3); border-radius: 12px; padding: 20px; margin: 24px 0; text-align: center;">
            <div style="font-size: 13px; color: #D4A345; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                Direct Live Meeting Access
            </div>
            <p style="margin: 0 0 16px 0; font-size: 14px; color: #e2e8f0;">
                Click below to join the live room when session time arrives:
            </p>
            <a href="{meeting_link}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #D4A345 0%, #E5A93C 100%); color: #080E1E; padding: 14px 32px; font-size: 15px; font-weight: 800; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 15px rgba(212, 163, 69, 0.3);">
                🎥 Join Live Meeting Room
            </a>
            <div style="margin-top: 12px; font-size: 12px; color: #94a3b8; word-break: break-all;">
                Or copy link: <a href="{meeting_link}" target="_blank" style="color: #60a5fa; text-decoration: underline;">{meeting_link}</a>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #64748b;">
                (Room opens 15 minutes before 8:00 PM EAT)
            </div>
        </div>
        """
    else:
        meeting_box = f"""
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 18px; margin: 24px 0;">
            <div style="font-size: 13px; color: #D4A345; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                Live Meeting Link Notice
            </div>
            <p style="margin: 0; font-size: 13px; color: #cbd5e1; line-height: 1.5;">
                The meeting room link (Google Meet / Zoom) is being prepared and will be active directly on the <a href="{reg_page_url}" style="color: #D4A345; font-weight: bold;">session page</a> and emailed to your inbox prior to the start time (8:00 PM EAT).
            </p>
        </div>
        """

    poster_html = ""
    if poster_url:
        poster_html = f"""
        <div style="margin: 20px 0; text-align: center;">
            <img src="{poster_url}" alt="{escape(topic)}" style="max-width: 100%; height: auto; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 10px 25px rgba(0,0,0,0.4);" />
        </div>
        """

    content = f"""
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="display: inline-block; padding: 4px 12px; border-radius: 999px; background: rgba(52, 211, 153, 0.15); color: #34d399; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border: 1px solid rgba(52, 211, 153, 0.3);">
                ✓ Registration Confirmed
            </span>
            <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 16px 0 8px 0; line-height: 1.3;">
                Hello {escape(full_name)},
            </h1>
            <p style="color: #94a3b8; font-size: 15px; margin: 0; line-height: 1.5;">
                {greeting_headline} {greeting_sub}
            </p>
        </div>

        <!-- Session Highlights Card -->
        <div style="background-color: #0e172e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="color: #D4A345; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">
                Session Details
            </div>
            <div style="color: #ffffff; font-size: 18px; font-weight: 700; margin-bottom: 12px; line-height: 1.4;">
                {escape(topic)}
            </div>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 12px;">
                <tr>
                    <td style="padding: 6px 0; font-size: 14px; color: #94a3b8; width: 30px;">📅</td>
                    <td style="padding: 6px 0; font-size: 14px; color: #e2e8f0; font-weight: 600;">{escape(session_date)}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-size: 14px; color: #94a3b8;">⏰</td>
                    <td style="padding: 6px 0; font-size: 14px; color: #e2e8f0; font-weight: 600;">8:00 PM — 9:30 PM EAT (East Africa Time)</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-size: 14px; color: #94a3b8;">🎟️</td>
                    <td style="padding: 6px 0; font-size: 14px; color: #34d399; font-weight: 600;">100% Free Masterclass</td>
                </tr>
            </table>
            {f'<p style="margin: 12px 0 0 0; font-size: 13px; color: #94a3b8; line-height: 1.6; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 12px;">{escape(desc)}</p>' if desc else ''}
        </div>

        {poster_html}

        {meeting_box}

        <!-- Calendar & Share Actions -->
        <div style="margin: 24px 0 20px 0; text-align: center;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="center">
                        <a href="{cal_url}" target="_blank" style="display: inline-block; background-color: #1e293b; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.15); padding: 12px 20px; font-size: 13px; font-weight: 600; text-decoration: none; border-radius: 8px; margin: 4px;">
                            📅 Add to Google Calendar
                        </a>
                        <a href="{wa_url}" target="_blank" style="display: inline-block; background-color: #059669; color: #ffffff; padding: 12px 20px; font-size: 13px; font-weight: 600; text-decoration: none; border-radius: 8px; margin: 4px;">
                            💬 Share via WhatsApp
                        </a>
                    </td>
                </tr>
            </table>
        </div>

        <div style="background: rgba(255,255,255,0.02); border-radius: 10px; padding: 16px; margin-top: 20px; font-size: 12px; color: #94a3b8; line-height: 1.6;">
            <strong style="color: #e2e8f0;">Explore More:</strong> Past recordings of Insighters Monday and expert masterclasses are published in our <a href="{clean_base}/recordings" style="color: #D4A345; text-decoration: underline;">Recordings Archive</a>.
        </div>
    """

    return wrap_email_layout(f"Seat Confirmed: Insighters Monday ({session_date})", content, clean_base)


def build_monday_broadcast_email(
    session_info: dict,
    custom_note: str = None,
    base_url: str = "https://insightcirclepalace.com",
) -> str:
    session_info = session_info or {}
    clean_base = (base_url or "https://insightcirclepalace.com").rstrip("/")
    topic = session_info.get("banner_short_description") or "Insighters Monday Live Masterclass"
    session_date = session_info.get("date") or "This Coming Monday · 8:00 PM EAT"
    desc = session_info.get("full_session_description") or "Join our weekly interactive masterclass exploring breakthrough ideas, industry execution, and leadership."
    meeting_link = (session_info.get("meeting_link") or "").strip()
    poster_url = (session_info.get("poster_url") or "").strip()
    reg_url = f"{clean_base}/monday-registration"

    poster_html = ""
    if poster_url:
        poster_html = f"""
        <div style="margin: 20px 0; text-align: center;">
            <img src="{poster_url}" alt="{escape(topic)}" style="max-width: 100%; height: auto; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 10px 25px rgba(0,0,0,0.4);" />
        </div>
        """

    custom_note_html = ""
    if custom_note and custom_note.strip():
        custom_note_html = f"""
        <div style="background: rgba(212, 163, 69, 0.08); border-left: 3px solid #D4A345; padding: 14px 18px; margin: 18px 0; border-radius: 0 8px 8px 0; color: #e2e8f0; font-size: 14px; line-height: 1.5;">
            {escape(custom_note.strip())}
        </div>
        """

    content = f"""
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="display: inline-block; padding: 4px 12px; border-radius: 999px; background: rgba(212, 163, 69, 0.15); color: #D4A345; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border: 1px solid rgba(212, 163, 69, 0.3);">
                🎙️ Upcoming Flagship Masterclass
            </span>
            <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 16px 0 8px 0; line-height: 1.3;">
                Insighters Monday Live Session
            </h1>
            <p style="color: #94a3b8; font-size: 15px; margin: 0; line-height: 1.5;">
                We are excited to invite you to our upcoming flagship masterclass!
            </p>
        </div>

        {custom_note_html}

        <!-- Topic Card -->
        <div style="background-color: #0e172e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 22px; margin-bottom: 20px;">
            <div style="color: #D4A345; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px;">
                Topic & Focus
            </div>
            <div style="color: #ffffff; font-size: 20px; font-weight: 700; margin-bottom: 14px; line-height: 1.4;">
                {escape(topic)}
            </div>
            <div style="font-size: 14px; color: #cbd5e1; margin-bottom: 12px;">
                📅 <strong>Date & Time:</strong> {escape(session_date)}
            </div>
            <div style="font-size: 14px; color: #34d399; margin-bottom: 14px;">
                🎟️ <strong>Admission:</strong> 100% Free & Open
            </div>
            <p style="margin: 0; font-size: 14px; color: #94a3b8; line-height: 1.6; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 12px;">
                {escape(desc)}
            </p>
        </div>

        {poster_html}

        <!-- Call to Action -->
        <div style="text-align: center; margin: 28px 0;">
            <a href="{reg_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #D4A345 0%, #E5A93C 100%); color: #080E1E; padding: 15px 36px; font-size: 16px; font-weight: 800; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 15px rgba(212, 163, 69, 0.3);">
                🎟️ Reserve Your Free Seat
            </a>
            {f'<div style="margin-top: 12px; font-size: 13px;"><a href="{meeting_link}" target="_blank" style="color: #60a5fa;">Direct Meeting Room Link &rarr;</a></div>' if meeting_link else ''}
        </div>
    """

    return wrap_email_layout(f"Upcoming Insighters Monday: {topic}", content, clean_base)


def build_monday_reminder_email(
    full_name: str,
    session_info: dict,
    custom_message: str = None,
    base_url: str = "https://insightcirclepalace.com",
) -> str:
    session_info = session_info or {}
    clean_base = (base_url or "https://insightcirclepalace.com").rstrip("/")
    topic = session_info.get("banner_short_description") or "Insighters Monday Live Masterclass"
    session_date = session_info.get("date") or "Tonight at 8:00 PM EAT"
    meeting_link = (session_info.get("meeting_link") or "").strip()

    custom_box = ""
    if custom_message and custom_message.strip():
        custom_box = f"""
        <div style="background: rgba(255, 255, 255, 0.04); border-left: 3px solid #60a5fa; padding: 14px 18px; margin: 18px 0; border-radius: 0 8px 8px 0; color: #e2e8f0; font-size: 14px; line-height: 1.5;">
            {escape(custom_message.strip())}
        </div>
        """

    meeting_cta = ""
    if meeting_link:
        meeting_cta = f"""
        <div style="text-align: center; margin: 28px 0;">
            <a href="{meeting_link}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #D4A345 0%, #E5A93C 100%); color: #080E1E; padding: 16px 36px; font-size: 16px; font-weight: 800; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 15px rgba(212, 163, 69, 0.3);">
                🎥 Click Here to Enter Meeting Room
            </a>
            <div style="margin-top: 12px; font-size: 12px; color: #94a3b8;">
                Direct Link: <a href="{meeting_link}" target="_blank" style="color: #60a5fa;">{meeting_link}</a>
            </div>
        </div>
        """
    else:
        meeting_cta = f"""
        <div style="text-align: center; margin: 24px 0;">
            <a href="{clean_base}/monday-registration" target="_blank" style="display: inline-block; background: #1e293b; color: #ffffff; padding: 14px 28px; font-size: 14px; font-weight: 700; text-decoration: none; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
                View Live Session Details
            </a>
        </div>
        """

    content = f"""
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="display: inline-block; padding: 4px 12px; border-radius: 999px; background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border: 1px solid rgba(239, 68, 68, 0.3);">
                🔴 Starting Soon
            </span>
            <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 16px 0 8px 0; line-height: 1.3;">
                Insighters Monday Masterclass
            </h1>
            <p style="color: #94a3b8; font-size: 15px; margin: 0;">
                Hello {escape(full_name)}, your live session is about to begin!
            </p>
        </div>

        {custom_box}

        <div style="background-color: #0e172e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="color: #D4A345; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px;">
                Tonight's Session
            </div>
            <div style="color: #ffffff; font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                {escape(topic)}
            </div>
            <div style="font-size: 14px; color: #94a3b8;">
                ⏰ <strong>Time:</strong> {escape(session_date)}
            </div>
        </div>

        {meeting_cta}
    """

    return wrap_email_layout(f"Starting Soon: Insighters Monday ({topic})", content, clean_base)

