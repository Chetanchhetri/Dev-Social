import os
from smtplib import SMTP, SMTPAuthenticationError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings

def send_otp_email(recipient_email: str, otp_code: str) -> bool:
    sender_email = settings.EMAIL_SENDER.strip()
    sender_password = settings.EMAIL_PASSWORD.replace(" ", "").strip()

    if not sender_email or not sender_password:
        print("Mail Error: Missing 'EMAIL_SENDER' or 'EMAIL_PASSWORD' inside .env file.")
        return False

    html_message = f"""
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .email-container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(90deg, #00ff8e 0%, #00c9ff 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; text-align: center; }}
            .otp-code {{ font-size: 36px; font-weight: 700; color: #00c9ff; font-family: monospace; letter-spacing: 8px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header"><h1>🔐 Verification Code</h1></div>
            <div class="content">
                <p>Use the OTP below to verify your account:</p>
                <div class="otp-code">{otp_code}</div>
                <p>This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = 'DevSocial - Email Verification OTP'
    msg.attach(MIMEText(html_message, 'html'))

    try:
        server = SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False