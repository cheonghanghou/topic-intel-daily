import smtplib
from email.header import Header
from email.mime.text import MIMEText


def send_email(subject, body, sender, password, to=None):
    to = to or sender
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [to], msg.as_string())
