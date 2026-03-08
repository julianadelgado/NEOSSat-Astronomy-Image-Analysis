from unittest.mock import MagicMock, patch


def test_send_email(email_service):
    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        email_service.send_email("user@example.com", "Subject", "Body")

        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)


def test_send_email_calls_starttls_and_login(email_service):
    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        email_service.send_email("user@example.com", "Subject", "Body")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@gmail.com", "password")


def test_send_email_failure_does_not_raise(email_service):
    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("connection refused")

        # Should print the error, not crash
        email_service.send_email("user@example.com", "Subject", "Body")
