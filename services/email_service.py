import os
import smtplib
from email.mime.text import MIMEText


class EmailService:
    def __init__(self):
        self.smtp_server = os.environ["SMTP_SERVER"]
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.username = os.environ["SMTP_USER"]
        self.password = os.environ["SMTP_PASSWORD"]

    def send_email(self, to_email, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = to_email

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_email, msg.as_string())
                print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
