"""
Dispatch Sender Module for Resonance.
Integrates with Gmail SMTP via GmailAuth, supports dry-run mode,
test send to configured recipient, transient vs permanent error classification,
and logs to sent_log.csv only upon confirmed SMTP acceptance.
"""

import os
import re
import socket
import smtplib
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from config import load_settings, PRESENTATION_PATH
from outreach.gmail_auth import GmailAuth
from outreach.attachment_handler import AttachmentHandler
from app_logging.activity_logger import ActivityLogger
from dispatch.models import DispatchQueueItem


class DispatchSender:
    """Handles low-level dispatch via Gmail SMTP or dry-run simulation."""

    def __init__(self, settings: Optional[Dict[str, Any]] = None, logger: Optional[ActivityLogger] = None):
        self.settings = settings or load_settings()
        self.logger = logger or ActivityLogger()

    def _sanitize_error(self, err_msg: str) -> str:
        """Strip sensitive credentials like app passwords from error strings."""
        if not err_msg:
            return ""
        app_pwd = self.settings.get("gmail_app_password", "")
        if app_pwd and app_pwd in err_msg:
            err_msg = err_msg.replace(app_pwd, "[REDACTED]")
        # Redact generic 16-character google app password pattern
        err_msg = re.sub(r'[a-z]{4}\s*[a-z]{4}\s*[a-z]{4}\s*[a-z]{4}', '[REDACTED]', err_msg, flags=re.IGNORECASE)
        return err_msg

    def _classify_error(self, exc: Exception) -> str:
        """
        Classify error into 'transient' (eligible for bounded retry)
        or 'permanent' (fatal, do not retry).
        """
        if isinstance(exc, (smtplib.SMTPAuthenticationError,)):
            return "permanent"
        if isinstance(exc, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, socket.timeout, TimeoutError)):
            return "transient"
        if isinstance(exc, smtplib.SMTPResponseException):
            # 4xx are transient, 5xx are permanent
            if 400 <= exc.smtp_code < 500:
                return "transient"
            return "permanent"
        err_str = str(exc).lower()
        if any(term in err_str for term in ["timeout", "connection reset", "broken pipe", "temporarily unavailable", "network"]):
            return "transient"
        return "permanent"

    def build_email_message(
        self,
        sender_email: str,
        recipient_email: str,
        recipient_name: str,
        company_name: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        is_test: bool = False,
        cc_email: Optional[str] = None
    ) -> EmailMessage:
        """Construct EmailMessage payload with presentation attachment."""
        msg = EmailMessage()
        clean_subject = f"[TEST OUTREACH] {subject}" if is_test else subject
        msg["Subject"] = clean_subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        if cc_email and cc_email.strip():
            msg["Cc"] = cc_email.strip()

        msg_id = f"<{uuid.uuid4().hex[:16]}@resonance.export>"
        msg["Message-ID"] = msg_id

        content_body = body
        if is_test:
            header_notice = (
                "--- [RESONANCE CONTROLLED TEST SEND] ---\n"
                f"Target Contact: {recipient_name}\n"
                f"Target Company: {company_name}\n"
                f"Original Target Email: {recipient_email}\n"
                "-----------------------------------------\n\n"
            )
            content_body = header_notice + body

        msg.set_content(content_body)

        # Attach presentation
        att_path = attachment_path or self.settings.get("presentation_path") or str(PRESENTATION_PATH)
        if att_path and AttachmentHandler.validate_file(att_path):
            AttachmentHandler.attach_presentation(msg, att_path)

        return msg

    def send_item(
        self,
        item: DispatchQueueItem,
        is_test: bool = False,
        test_recipient: Optional[str] = None,
        smtp_server: Optional[Any] = None
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Send a queue item.
        Returns: (success, smtp_message_id, error_message, error_category)
        """
        dry_run = bool(self.settings.get("dry_run", True))
        sender_email = (self.settings.get("gmail_email") or "").strip()
        app_password = (self.settings.get("gmail_app_password") or "").strip()
        cc_email = (self.settings.get("monitoring_cc_email") or "").strip()

        target_recipient = (test_recipient if is_test else item.recipient_email).strip().lower()

        # Handle DRY RUN
        if dry_run and not is_test:
            mock_id = f"<dry-run-{uuid.uuid4().hex[:12]}@resonance.local>"
            return True, mock_id, None, None

        if not sender_email or not app_password:
            return False, None, "Gmail credentials not configured.", "permanent"

        msg = self.build_email_message(
            sender_email=sender_email,
            recipient_email=target_recipient,
            recipient_name=item.recipient_name,
            company_name=item.company_name,
            subject=item.subject,
            body=item.body,
            attachment_path=item.attachment_path,
            is_test=is_test,
            cc_email=cc_email if not is_test else None
        )

        server_provided = smtp_server is not None
        server = smtp_server

        try:
            if not server:
                server, auth_err = GmailAuth.connect_and_login(sender_email, app_password)
                if auth_err or not server:
                    return False, None, self._sanitize_error(auth_err or "SMTP Auth Failed"), "permanent"

            server.send_message(msg)
            msg_id = msg.get("Message-ID") or f"<{uuid.uuid4().hex[:16]}@gmail.com>"

            # Log to sent_log.csv ONLY if real send and successfully sent
            if not is_test and not dry_run:
                self.logger.log_send_attempt(
                    email=item.recipient_email,
                    status="sent",
                    subject=item.subject,
                    error_message=""
                )

            return True, msg_id, None, None

        except Exception as exc:
            err_cat = self._classify_error(exc)
            err_msg = self._sanitize_error(str(exc))

            if not is_test and not dry_run and err_cat == "permanent":
                self.logger.log_send_attempt(
                    email=item.recipient_email,
                    status="failed",
                    subject=item.subject,
                    error_message=err_msg
                )

            return False, None, err_msg, err_cat

        finally:
            if server and not server_provided:
                try:
                    server.quit()
                except Exception:
                    pass
