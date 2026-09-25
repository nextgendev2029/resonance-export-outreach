"""
Gmail Authentication Module.
Connects to Gmail SMTP with App Password authentication, supporting STARTTLS
and SSL fallback.
"""

import smtplib
from typing import Tuple, Optional
from config import SMTP_HOST, SMTP_PORT_STARTTLS, SMTP_PORT_SSL, load_settings


class GmailAuth:
    @staticmethod
    def connect_and_login(
        email: str = None,
        app_password: str = None,
        use_ssl: bool = False
    ) -> Tuple[Optional[smtplib.SMTP], Optional[str]]:
        """
        Establish authenticated SMTP connection.
        Returns: (smtp_client, error_message)
        """
        settings = load_settings()
        user_email = (email or settings.get("gmail_email", "")).strip()
        user_pwd = (app_password or settings.get("gmail_app_password", "")).replace(" ", "").strip()

        if not user_email or not user_pwd:
            return None, "Gmail email or App Password not configured."

        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT_SSL, timeout=15)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT_STARTTLS, timeout=15)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(user_email, user_pwd)
            return server, None

        except smtplib.SMTPAuthenticationError as e:
            return None, f"SMTP Authentication failed: Invalid Gmail address or App Password ({e.smtp_code})"
        except smtplib.SMTPConnectError as e:
            # Fallback to SSL if STARTTLS connection failed
            if not use_ssl:
                return GmailAuth.connect_and_login(email, app_password, use_ssl=True)
            return None, f"Could not connect to SMTP server: {e}"
        except Exception as e:
            if not use_ssl:
                return GmailAuth.connect_and_login(email, app_password, use_ssl=True)
            return None, f"Connection error: {str(e)}"
