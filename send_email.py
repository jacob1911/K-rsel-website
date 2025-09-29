import smtplib
from email.mime.text import MIMEText


def message_to_email(msg, recipient, sender):
    # Create plain text email
    mime_msg = MIMEText(msg, "plain")
    # Add headers
    mime_msg["From"] = sender   # (display name, address)
    mime_msg["To"] = recipient
    mime_msg["Subject"] = f"{sender} asked to drive with you"
    
    return mime_msg


def send_mail(mime_msg, smtp_user, smtp_pass):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(mime_msg)
        server.quit()

    print(":::: EMAIL SENT ::::")

def send_2oath_email(msg, recipient, sender, smtp_user, smtp_pass):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(mime_msg)
        server.quit()
