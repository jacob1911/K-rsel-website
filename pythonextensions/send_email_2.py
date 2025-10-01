# app_only_smtp.py
import os, base64, smtplib
from email.message import EmailMessage
import dotenv
import msal

dotenv.load_dotenv("environ.env")

TENANT_ID  = os.environ["TENANT_ID"]
CLIENT_ID  = os.environ["CLIENT_ID"]
CLIENT_SEC = os.environ["CLIENT_SECRET"]   # consider using a certificate in production
AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE      = ["https://outlook.office365.com/.default"]  # app-only for SMTP
SMTP_HOST  = "smtp.office365.com"
SMTP_PORT  = 587
SENDER     = "jast@do-f.dk"  # the single org mailbox you want to send from

def xoauth2_b64(user_email, access_token):
    # SASL XOAUTH2 requires this exact format with \x01 (Ctrl+A) separators
    s = f"user={user_email}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(s.encode()).decode()

def send_mail(to_addr, subject, body):
    # 1) Get a short-lived access token via client credentials (no user interaction)
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SEC
    )
    token = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in token:
        raise RuntimeError(f"Token acquisition failed: {token}")

    # 2) Build the message
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    # 3) SMTP with XOAUTH2
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo(); s.starttls(); s.ehlo()
        xoauth = xoauth2_b64(SENDER, token["access_token"])
        code, resp = s.docmd("AUTH", "XOAUTH2 " + xoauth)
        if code != 235:
            raise RuntimeError(f"SMTP AUTH failed: {code} {resp}")
        s.send_message(msg)

# Example:
# send_mail("recipient@example.com", "Test", "Hello from app-only SMTP OAuth2")
