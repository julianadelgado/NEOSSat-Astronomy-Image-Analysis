import os
import shutil
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

TASK_LABELS = {
    "image_stacking": ("Image stacking", "Empilement d'images"),
    "stars": ("Star detection", "Détection d'étoiles"),
    "streaks": ("Streak detection", "Détection de traînées"),
}


class EmailService:
    def __init__(self, smtp_server, smtp_port, username, password, reports_dir):
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port)
        self.username = username
        self.password = password
        self.reports_dir = reports_dir

    def send_email(self, to_email, subject, body, attachment_path=None):
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}",
            )
            msg.attach(part)

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

        zip_filename = "reports_directory"
        shutil.make_archive(zip_filename, "zip", self.reports_dir)
        full_zip_path = f"{zip_filename}.zip"

        subject = "NEOSSat-Astronomy-Image-Analysis-Notification"
        body = (
            f"This notification is to inform you that the following tasks have finished running: {', '.join(labels_en)}.\n\n"
            f"Cette notification est pour vous informer que les tâches suivantes ont terminé leur exécution : {', '.join(labels_fr)}."
        )
        self.send_email(to_email, subject, body, full_zip_path)

        if os.path.exists(full_zip_path):
            os.remove(full_zip_path)
