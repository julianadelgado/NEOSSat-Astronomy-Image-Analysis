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

def test_send_completion_notification_formats_email_correctly(notification_service):
    with patch.object(notification_service, "send_email") as mock_send_email:
        notification_service.send_completion_notification(
            "user@example.com", ["image_stacking", "stars"]
        )

        mock_send_email.assert_called_once()
        args, _ = mock_send_email.call_args
        to_email, subject, body = args
        assert to_email == "user@example.com"
        assert subject == "NEOSSat-Astronomy-Image-Analysis-Notification"
        assert "Image stacking" in body
        assert "Star detection" in body
        assert "Empilement d'images" in body
        assert "Détection d'étoiles" in body