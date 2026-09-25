"""
Report Generator Module.
Generates campaign performance summaries, metrics, and CSV report exports.
"""

import io
import csv
from typing import Dict, Any, List
from app_logging.activity_logger import ActivityLogger


class ReportGenerator:
    def __init__(self, logger: ActivityLogger = None):
        self.logger = logger or ActivityLogger()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate high-level operational statistics and run summary."""
        stats = self.logger.get_summary_statistics()
        logs = self.logger.get_sent_logs()

        # Last 10 activity log entries
        recent_activity = logs[-10:] if logs else []
        recent_activity.reverse()

        return {
            "statistics": stats,
            "recent_activity": recent_activity
        }

    def generate_csv_report(self) -> str:
        """Stream the full outreach and buyer report as CSV string."""
        buyers = self.logger.get_all_buyers()
        logs = self.logger.get_sent_logs()

        # Map last log per email
        last_log = {}
        for l in logs:
            last_log[l.get("email", "").lower()] = l

        output = io.StringIO()
        fieldnames = [
            "lead_id",
            "email",
            "buyer_name",
            "company_name",
            "website",
            "country",
            "source_platform",
            "source_url",
            "validation_status",
            "classification",
            "outreach_status",
            "is_demo",
            "last_contact_timestamp",
            "error_detail",
            "notes"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for b in buyers:
            e = b.get("email", "").lower()
            log_entry = last_log.get(e, {})
            row = {
                "lead_id": b.get("lead_id", ""),
                "email": b.get("email", ""),
                "buyer_name": b.get("buyer_name", ""),
                "company_name": b.get("company_name", ""),
                "website": b.get("website", ""),
                "country": b.get("country", ""),
                "source_platform": b.get("source_platform", ""),
                "source_url": b.get("source_url", ""),
                "validation_status": b.get("validation_status", ""),
                "classification": b.get("classification", ""),
                "outreach_status": b.get("outreach_status", ""),
                "is_demo": b.get("is_demo", "false"),
                "last_contact_timestamp": log_entry.get("timestamp", ""),
                "error_detail": log_entry.get("error_message", ""),
                "notes": b.get("notes", "")
            }
            writer.writerow(row)

        return output.getvalue()
