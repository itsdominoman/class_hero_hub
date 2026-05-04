import smtplib
from email.message import EmailMessage
from .database import settings
import logging

logger = logging.getLogger(__name__)

def send_invite_email(to_email: str, inviter_name: str, invite_url: str):
    """
    Sends a family invite email using SMTP settings.
    """
    if not settings.SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not set, skipping email send")
        return False

    msg = EmailMessage()
    msg['Subject'] = f"You've been invited to Family Hero Hub"
    msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg['To'] = to_email

    # Plain text version
    text_content = f"""
Hello!

{inviter_name} has invited you to help manage their family on Family Hero Hub.

Family Hero Hub helps families track chores, awards, and hero progress in a fun way!

To accept this invitation and join the family, please click the link below:

{invite_url}

This link will expire in {settings.INVITE_EXPIRY_DAYS} days.

If you weren't expecting this invitation, you can safely ignore this email.

Best,
The Family Hero Hub Team
"""
    msg.set_content(text_content)

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #FF5A5F; 
            color: white; 
            text-decoration: none; 
            border-radius: 8px; 
            font-weight: bold;
        }}
        .footer {{ margin-top: 30px; font-size: 0.8em; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>You've been invited!</h2>
        <p>Hello!</p>
        <p><strong>{inviter_name}</strong> has invited you to help manage their family on <strong>Family Hero Hub</strong>.</p>
        <p>Family Hero Hub helps families track chores, awards, and hero progress in a fun way!</p>
        <p>To accept this invitation and join the family, please click the button below:</p>
        <p>
            <a href="{invite_url}" class="button">Accept Invitation</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p><a href="{invite_url}">{invite_url}</a></p>
        <p><em>This link will expire in {settings.INVITE_EXPIRY_DAYS} days.</em></p>
        <p>If you weren't expecting this invitation, you can safely ignore this email.</p>
        <div class="footer">
            <p>&copy; {2026} Family Hero Hub</p>
        </div>
    </div>
</body>
</html>
"""
    msg.add_alternative(html_content, subtype='html')

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_STARTTLS:
                    server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        logger.info(f"Invite email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invite email to {to_email}: {e}")
        return False

def send_registration_notification(request_details: dict):
    """
    Sends a notification to support about a new registration request.
    """
    if not settings.SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not set, skipping registration notification")
        return False

    msg = EmailMessage()
    msg['Subject'] = "New Family Hero Hub Registration Request"
    msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg['To'] = "support@familyherohub.com"

    content = f"""
New registration request received:

Name: {request_details.get('name')}
Email: {request_details.get('email')}
Family Name: {request_details.get('family_name')}
Message: {request_details.get('message', 'N/A')}

Review this request in the admin dashboard:
{settings.PUBLIC_APP_URL.rstrip('/')}/admin/registration-requests
"""
    msg.set_content(content)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_STARTTLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send registration notification: {e}")
        return False

def send_approval_email(to_email: str, name: str):
    """
    Sends an approval email to the user.
    """
    if not settings.SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not set, skipping approval email")
        return False

    msg = EmailMessage()
    msg['Subject'] = "Your Family Hero Hub access has been approved!"
    msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg['To'] = to_email

    text_content = f"""
Hello {name}!

Great news! Your request for access to Family Hero Hub has been approved.

You can now log in using your Google account at:
{settings.PUBLIC_APP_URL.rstrip('/')}/login

We're excited to have you on board!

Best,
The Family Hero Hub Team
"""
    msg.set_content(text_content)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_STARTTLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send approval email to {to_email}: {e}")
        return False
