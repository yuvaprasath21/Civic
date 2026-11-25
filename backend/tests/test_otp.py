"""
OTP tests. Real providers are replaced with in-memory fakes that record
what would have been sent, so tests can read the code without any
email/SMS account.
"""
from datetime import timedelta

import pytest

from app.services.delivery.base import DeliveryError, EmailProvider, SMSProvider


class FakeEmail(EmailProvider):
    def __init__(self):
        self.sent = []

    def send(self, to_email, subject, body):
        self.sent.append((to_email, body))


class FakeSMS(SMSProvider):
    def __init__(self):
        self.sent = []

    def send(self, to_number, body):
        self.sent.append((to_number, body))


def _code_from(body: str) -> str:
    import re
    return re.search(r"code is (\d+)", body).group(1)


@pytest.fixture()
def providers(monkeypatch):
    email, sms = FakeEmail(), FakeSMS()
    monkeypatch.setattr("app.services.otp_service.get_email_provider", lambda: email)
    monkeypatch.setattr("app.services.otp_service.get_sms_provider", lambda: sms)
    return email, sms


EMAIL = "meera.iyer@example.com"
MOBILE = "+919876543210"


def test_send_otp_to_email_and_mobile_with_separate_codes(client, providers):
    email, sms = providers
    r = client.post("/api/auth/send-otp", json={"email": EMAIL, "mobile": MOBILE})
    assert r.status_code == 200
    body = r.json()
    assert body["email_sent"] and body["mobile_sent"]
    assert body["expires_in_seconds"] == 300
    assert len(email.sent) == 1 and len(sms.sent) == 1
    assert email.sent[0][0] == EMAIL and sms.sent[0][0] == MOBILE
    assert len(_code_from(email.sent[0][1])) == 6
    # Independent codes per channel (collision odds are 1 in a million per run)
    assert _code_from(email.sent[0][1]) != _code_from(sms.sent[0][1])


def test_response_never_contains_the_otp(client, providers):
    email, _ = providers
    r = client.post("/api/auth/send-otp", json={"email": EMAIL})
    code = _code_from(email.sent[0][1])
    assert code not in r.text


def test_code_is_stored_hashed_not_plaintext(client, providers, db_session):
    from app.models.otp import OtpVerification

    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    code = _code_from(email.sent[0][1])
    row = db_session.query(OtpVerification).one()
    assert code not in row.code_hash
    assert len(row.code_hash) == 64


def test_requires_at_least_one_destination(client, providers):
    r = client.post("/api/auth/send-otp", json={})
    assert r.status_code == 422
    assert r.json()["error_code"] == "NO_DESTINATION"


@pytest.mark.parametrize("bad", ["9876543210", "+0123456789", "abc", "+91"])
def test_rejects_non_e164_mobile(client, providers, bad):
    r = client.post("/api/auth/send-otp", json={"mobile": bad})
    assert r.status_code == 422


def test_mobile_spaces_and_dashes_are_normalised(client, providers):
    _, sms = providers
    r = client.post("/api/auth/send-otp", json={"mobile": "+91 98765-43210"})
    assert r.status_code == 200
    assert sms.sent[0][0] == "+919876543210"


def test_verify_email_otp_success_marks_user_verified(client, providers, db_session):
    from app.models.user import User

    client.post("/api/auth/register", json={"full_name": "Meera Iyer", "email": EMAIL, "password": "SecurePass123"})
    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    code = _code_from(email.sent[0][1])

    r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": code})
    assert r.status_code == 200
    assert db_session.query(User).filter(User.email == EMAIL).one().is_email_verified is True


def test_verify_mobile_otp_success_marks_user_phone_verified(client, providers, db_session):
    from app.models.user import User

    client.post(
        "/api/auth/register",
        json={"full_name": "Meera Iyer", "email": EMAIL, "phone_number": MOBILE, "password": "SecurePass123"},
    )
    _, sms = providers
    client.post("/api/auth/send-otp", json={"mobile": MOBILE})
    code = _code_from(sms.sent[0][1])

    r = client.post("/api/auth/verify-mobile-otp", json={"mobile": MOBILE, "otp": code})
    assert r.status_code == 200
    assert db_session.query(User).filter(User.email == EMAIL).one().is_phone_verified is True


def test_email_code_does_not_verify_mobile(client, providers):
    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL, "mobile": MOBILE})
    email_code = _code_from(email.sent[0][1])
    r = client.post("/api/auth/verify-mobile-otp", json={"mobile": MOBILE, "otp": email_code})
    assert r.status_code == 422
    assert r.json()["error_code"] == "OTP_INCORRECT"


def test_wrong_code_rejected_and_attempts_limited(client, providers, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OTP_MAX_ATTEMPTS", 3)
    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    real = _code_from(email.sent[0][1])
    wrong = "000000" if real != "000000" else "111111"

    for _ in range(3):
        r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": wrong})
        assert r.json()["error_code"] == "OTP_INCORRECT"

    # Locked out: even the CORRECT code is now refused.
    r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": real})
    assert r.status_code == 422
    assert r.json()["error_code"] == "OTP_TOO_MANY_ATTEMPTS"


def test_code_is_single_use(client, providers):
    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    code = _code_from(email.sent[0][1])
    assert client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": code}).status_code == 200
    r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": code})
    assert r.status_code == 422
    assert r.json()["error_code"] == "OTP_INVALID_OR_EXPIRED"


def test_expired_code_rejected(client, providers, db_session):
    from datetime import datetime, timezone

    from app.models.otp import OtpVerification

    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    code = _code_from(email.sent[0][1])
    row = db_session.query(OtpVerification).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": code})
    assert r.status_code == 422
    assert r.json()["error_code"] == "OTP_INVALID_OR_EXPIRED"


def test_resend_cooldown_enforced(client, providers):
    assert client.post("/api/auth/send-otp", json={"email": EMAIL}).status_code == 200
    r = client.post("/api/auth/resend-otp", json={"email": EMAIL})
    assert r.status_code == 429
    assert r.json()["error_code"] == "OTP_RESEND_COOLDOWN"


def test_resend_after_cooldown_invalidates_old_code(client, providers, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 0)
    email, _ = providers
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    old = _code_from(email.sent[0][1])
    client.post("/api/auth/resend-otp", json={"email": EMAIL})
    new = _code_from(email.sent[1][1])

    if old != new:  # a 1-in-a-million collision would make this check meaningless
        r = client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": old})
        assert r.status_code == 422
    assert client.post("/api/auth/verify-email-otp", json={"email": EMAIL, "otp": new}).status_code == 200


def test_delivery_failure_returns_502_and_leaves_no_live_code(client, monkeypatch, db_session):
    from app.models.otp import OtpVerification

    class Broken(EmailProvider):
        def send(self, to_email, subject, body):
            raise DeliveryError("smtp down")

    monkeypatch.setattr("app.services.otp_service.get_email_provider", lambda: Broken())
    r = client.post("/api/auth/send-otp", json={"email": EMAIL})
    assert r.status_code == 502
    assert r.json()["error_code"] == "OTP_DELIVERY_FAILED"
    assert "smtp down" not in r.text  # internal reason not leaked to the client
    assert db_session.query(OtpVerification).filter(OtpVerification.is_used.is_(False)).count() == 0


def test_console_provider_refuses_to_run_outside_development(monkeypatch):
    from app.core.config import settings
    from app.services.delivery.console import ConsoleEmailProvider

    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(DeliveryError):
        ConsoleEmailProvider().send("a@b.com", "s", "b")


def test_smtp_provider_reports_missing_credentials(monkeypatch):
    from app.core.config import settings
    from app.services.delivery.smtp_email import SMTPEmailProvider

    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    with pytest.raises(DeliveryError, match="not configured"):
        SMTPEmailProvider().send("a@b.com", "s", "b")


def test_twilio_provider_reports_missing_credentials(monkeypatch):
    from app.core.config import settings
    from app.services.delivery.twilio_sms import TwilioSMSProvider

    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "")
    with pytest.raises(DeliveryError, match="not configured"):
        TwilioSMSProvider().send("+919876543210", "hi")
