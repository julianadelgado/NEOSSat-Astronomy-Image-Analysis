import os
import smtplib
from email.mime.text import MIMEText

TASK_LABELS = {
    "image_stacking": ("Image stacking", "Empilement d'images"),
    "stars": ("Star detection", "Détection d'étoiles"),
    "streaks": ("Streak detection", "Détection de traînées"),
}


class EmailService:
    def __init__(self):
        self.smtp_server = os.environ["SMTP_SERVER"]
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.username = os.environ["SMTP_USER"]
        self.password = os.environ["SMTP_PASSWORD"]

    def send_email(self, to_email, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = to_email

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_email, msg.as_string())
                print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_completion_notification(self, to_email: str, completed_tasks: list[str]):
        labels_en = [TASK_LABELS[t][0] for t in completed_tasks if t in TASK_LABELS]
        labels_fr = [TASK_LABELS[t][1] for t in completed_tasks if t in TASK_LABELS]

        subject = "NEOSSat-Astronomy-Image-Analysis-Notification"
        body = (
            f"This notification is to inform you that the following tasks have finished running: {', '.join(labels_en)}.\n\n"
            f"Cette notification est pour vous informer que les tâches suivantes ont terminé leur exécution : {', '.join(labels_fr)}."
        )
        self.send_email(to_email, subject, body)
