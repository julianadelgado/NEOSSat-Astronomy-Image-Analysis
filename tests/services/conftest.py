import pytest
from services.email_service import EmailService


@pytest.fixture
def email_service(monkeypatch):
    monkeypatch.setenv("SMTP_SERVER", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    return EmailService()
