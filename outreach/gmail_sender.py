"""
Gmail Sender Module.
Orchestrates outreach campaigns, personalization, attachment injection,
duplicate prevention, reconnection handling, and delivery logging.
"""

import smtplib
import time
from email.message import EmailMessage
from typing import List, Dict, Any, Callable, Optional

from config import load_settings
from outreach.gmail_auth import GmailAuth
from outreach.attachment_handler import AttachmentHandler
from app_logging.activity_logger import ActivityLogger


class GmailSender:
    def __init__(self, logger: ActivityLogger = None):
        self.logger = logger or ActivityLogger()

    def build_message(
        self,
        sender_email: str,
        recipient: Dict[str, str],
        subject_template: str,
        body_template: str,
        cc_email: str = None,
        presentation_path: str = None
    ) -> EmailMessage:
        """Compose a personalized EmailMessage."""
        buyer_name = recipient.get("buyer_name") or "Valued Partner"
        company_name = recipient.get("company_name") or "Your Organization"
        to_email = recipient.get("email", "").strip()

        # Perform template substitution
        subject = subject_template.replace("{{buyer_name}}", buyer_name).replace("{{company_name}}", company_name)
        body = body_template.replace("{{buyer_name}}", buyer_name).replace("{{company_name}}", company_name).replace("{{email}}", to_email)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        if cc_email and cc_email.strip():
            msg["Cc"] = cc_email.strip()

        msg.set_content(body)

        # Attach presentation if available
        if presentation_path and AttachmentHandler.validate_file(presentation_path):
            AttachmentHandler.attach_presentation(msg, presentation_path)

        return msg

    def send_campaign(
        self,
        audience: str = "business",
        subject: str = None,
        body: str = None,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute an outreach campaign.
        Arguments:
            audience: 'business', 'individual', or 'all'
            subject: Email subject with optional {{buyer_name}} {{company_name}} tags
            body: Email body with optional template tags
            progress_callback: Optional callback fn(current_index, total, current_email, status)
        """
        settings = load_settings()
        sender_email = settings.get("gmail_email", "").strip()
        app_password = settings.get("gmail_app_password", "").strip()
        cc_email = settings.get("monitoring_cc_email", "").strip()
        delay = int(settings.get("send_delay_seconds", 5))
        daily_limit = int(settings.get("daily_send_limit", 100))
        presentation_path = settings.get("presentation_path")

        subject = subject or settings.get("default_subject", "")
        body = body or settings.get("default_body", "")

        # Target recipients from activity logger
        all_candidates = self.logger.get_classified_emails(audience)
        sent_set = self.logger.get_sent_emails()

        # Filter out already sent records (Duplicate prevention) and demo leads
        to_send: List[Dict[str, str]] = []
        duplicates_skipped = 0
        demo_suppressed = 0

        for rec in all_candidates:
            email = rec.get("email", "").strip().lower()
            if not email:
                continue

            # CRITICAL SAFETY CHECK: Never dispatch outreach to demo/sample contacts
            if str(rec.get("is_demo", "")).lower() == "true":
                demo_suppressed += 1
                continue

            if email in sent_set:
                duplicates_skipped += 1
                self.logger.log_send_attempt(email, "duplicate_skipped", subject, "Previously contacted")
            else:
                to_send.append(rec)

        # Apply daily limit
        to_send = to_send[:daily_limit]
        total = len(to_send)

        successful = []
        failed = []

        if total == 0:
            msg = "No new real recipients to send to."
            if demo_suppressed > 0:
                msg += f" ({demo_suppressed} demo leads safely excluded from dispatch)."
            return {
                "total_queued": 0,
                "duplicates_skipped": duplicates_skipped,
                "demo_suppressed": demo_suppressed,
                "success_count": 0,
                "failed_count": 0,
                "successful": [],
                "failed": [],
                "message": msg
            }

        # Authenticate
        server, auth_err = GmailAuth.connect_and_login(sender_email, app_password)
        if auth_err or not server:
            # Mark all as failed due to auth failure
            for i, rec in enumerate(to_send):
                e = rec.get("email", "")
                self.logger.log_send_attempt(e, "failed", subject, auth_err or "Authentication error")
                failed.append({"email": e, "error": auth_err or "Authentication error"})
                if progress_callback:
                    progress_callback(i + 1, total, e, "failed")

            return {
                "total_queued": total,
                "duplicates_skipped": duplicates_skipped,
                "demo_suppressed": demo_suppressed,
                "success_count": 0,
                "failed_count": total,
                "successful": [],
                "failed": failed,
                "error": auth_err
            }

        try:
            for idx, rec in enumerate(to_send):
                rec_email = rec.get("email", "")
                msg = self.build_message(
                    sender_email=sender_email,
                    recipient=rec,
                    subject_template=subject,
                    body_template=body,
                    cc_email=cc_email,
                    presentation_path=presentation_path
                )

                send_success = False
                err_msg = ""

                # Attempt send with automatic reconnect on disconnect
                for attempt in range(2):
                    try:
                        server.send_message(msg)
                        send_success = True
                        break
                    except smtplib.SMTPServerDisconnected:
                        # Reconnect and retry
                        server, reconn_err = GmailAuth.connect_and_login(sender_email, app_password)
                        if reconn_err:
                            err_msg = f"Reconnect failed: {reconn_err}"
                            break
                    except Exception as e:
                        err_msg = str(e)
                        break

                if send_success:
                    successful.append(rec_email)
                    self.logger.log_send_attempt(rec_email, "sent", subject)
                    if progress_callback:
                        progress_callback(idx + 1, total, rec_email, "sent")
                else:
                    failed.append({"email": rec_email, "error": err_msg})
                    self.logger.log_send_attempt(rec_email, "failed", subject, err_msg)
                    if progress_callback:
                        progress_callback(idx + 1, total, rec_email, "failed")

                # Respect delay between sends
                if idx < total - 1 and delay > 0:
                    time.sleep(delay)

        finally:
            try:
                server.quit()
            except Exception:
                pass

        return {
            "total_queued": total,
            "duplicates_skipped": duplicates_skipped,
            "demo_suppressed": demo_suppressed,
            "success_count": len(successful),
            "failed_count": len(failed),
            "successful": successful,
            "failed": failed
        }
