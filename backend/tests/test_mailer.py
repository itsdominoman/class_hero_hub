from unittest.mock import MagicMock

from app.mailer import StaffInviteEmail, send_staff_invite


def _invite() -> StaffInviteEmail:
    return StaffInviteEmail(
        to_email="new-admin@example.com",
        school_name="Example School",
        accept_url="https://class.familyherohub.com/invite/abc123",
    )


def test_send_staff_invite_skips_when_smtp_not_configured(monkeypatch, caplog):
    monkeypatch.setattr("app.mailer.settings.SMTP_HOST", "")
    monkeypatch.setattr("app.mailer.settings.SMTP_FROM_EMAIL", "")
    smtp_cls = MagicMock()
    monkeypatch.setattr("smtplib.SMTP", smtp_cls)

    with caplog.at_level("WARNING"):
        send_staff_invite(_invite())

    smtp_cls.assert_not_called()
    assert "SMTP not configured" in caplog.text


def test_send_staff_invite_sends_via_starttls_on_587(monkeypatch):
    monkeypatch.setattr("app.mailer.settings.SMTP_HOST", "mail.familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_PORT", 587)
    monkeypatch.setattr("app.mailer.settings.SMTP_USERNAME", "support@familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_PASSWORD", "secret")
    monkeypatch.setattr("app.mailer.settings.SMTP_FROM_EMAIL", "support@familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_FROM_NAME", "Class Hero Hub")
    monkeypatch.setattr("app.mailer.settings.SMTP_USE_TLS", True)

    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_cls = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr("smtplib.SMTP", smtp_cls)
    smtp_ssl_cls = MagicMock()
    monkeypatch.setattr("smtplib.SMTP_SSL", smtp_ssl_cls)

    invite = _invite()
    send_staff_invite(invite)

    smtp_cls.assert_called_once_with("mail.familyherohub.com", 587, timeout=10)
    smtp_ssl_cls.assert_not_called()
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("support@familyherohub.com", "secret")
    assert smtp_instance.send_message.call_count == 1
    sent_message = smtp_instance.send_message.call_args[0][0]
    assert sent_message["To"] == invite.to_email
    assert invite.accept_url in sent_message.get_content()


def test_send_staff_invite_uses_ssl_on_465(monkeypatch):
    monkeypatch.setattr("app.mailer.settings.SMTP_HOST", "mail.familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_PORT", 465)
    monkeypatch.setattr("app.mailer.settings.SMTP_USERNAME", "support@familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_PASSWORD", "secret")
    monkeypatch.setattr("app.mailer.settings.SMTP_FROM_EMAIL", "support@familyherohub.com")
    monkeypatch.setattr("app.mailer.settings.SMTP_USE_TLS", True)

    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_ssl_cls = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr("smtplib.SMTP_SSL", smtp_ssl_cls)
    smtp_cls = MagicMock()
    monkeypatch.setattr("smtplib.SMTP", smtp_cls)

    send_staff_invite(_invite())

    smtp_ssl_cls.assert_called_once_with("mail.familyherohub.com", 465, timeout=10)
    smtp_cls.assert_not_called()
    smtp_instance.starttls.assert_not_called()
