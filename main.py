"""
Resonance: CLI Pipeline Orchestrator.
Orchestrates: Discovery -> Extraction -> Validation -> Classification -> Outreach -> Reporting.
Target Business: Singing Bowls Export Outreach & Lead Operations.
"""

import sys
import argparse
from typing import List

from config import load_settings
from search.discovery_engine import DiscoveryEngine
from app_logging.activity_logger import ActivityLogger
from classification.ai_classifier import AIClassifier
from outreach.gmail_sender import GmailSender
from reports.report_generator import ReportGenerator


def run_pipeline(keyword: str = None, qualifiers: List[str] = None, sources: List[str] = None, run_outreach: bool = False):
    settings = load_settings()
    keyword = keyword or settings.get("search_keyword", "Singing Bowls")
    qualifiers = qualifiers or settings.get("default_qualifiers", [])
    logger = ActivityLogger()
    discovery_engine = DiscoveryEngine(logger)
    report_gen = ReportGenerator(logger)

    print("=" * 70)
    print("  RESONANCE - EXPORT OUTREACH & LEAD OPERATIONS (CLI)")
    print(f"  Target Product: Singing Bowls | Keyword: '{keyword}'")
    print(f"  Qualifiers: {', '.join(qualifiers)}")
    print("=" * 70)

    # 1. Buyer Discovery
    print(f"\n[1/5] Initiating Multi-Channel Buyer Discovery...")
    res = discovery_engine.execute_discovery(
        keyword=keyword,
        qualifiers=qualifiers,
        enabled_sources=sources,
        max_results_per_source=5
    )
    print(f"  -> Discovered: {res['raw_result_count']} raw results")
    print(f"  -> Extracted: {res['extracted_lead_count']} leads ({res['valid_email_count']} valid emails)")
    print(f"  -> Ingested: {res['new_leads_added']} new leads ({res['duplicate_count']} duplicates suppressed)")

    # 2. AI Classification
    print("\n[2/5] Running AI Classification (Business vs Individual)...")
    classifier = AIClassifier()
    unclassified = [b for b in logger.get_all_buyers() if b.get("classification") in ("Unclassified", "", None)]
    if unclassified:
        print(f"  -> Classifying {len(unclassified)} unclassified records...")
        bus, ind = classifier.classify_records(unclassified)
        logger.save_classified_emails(bus, ind)
        print(f"     Classified {len(bus)} as Business, {len(ind)} as Individual.")
    else:
        print("  -> All existing records are already classified.")

    # 3. Outreach Dispatch (optional via --send flag)
    if run_outreach:
        print("\n[3/5] Initiating Gmail Outreach Dispatch...")
        sender = GmailSender(logger)
        res_outreach = sender.send_campaign(audience="business")
        print(f"  -> Sent: {res_outreach['success_count']} | Failed: {res_outreach['failed_count']} | Duplicates Skipped: {res_outreach['duplicates_skipped']}")
        if res_outreach.get("demo_suppressed", 0) > 0:
            print(f"  -> Demo safety: {res_outreach['demo_suppressed']} demo leads suppressed.")
    else:
        print("\n[3/5] Outreach dispatch skipped (Use --send flag or Web UI to launch campaign).")

    # 4. Reporting
    print("\n[4/5] Operational Summary:")
    stats = report_gen.generate_summary()["statistics"]
    print(f"  • Total Leads in Database: {stats['total_leads']} ({stats['real_leads_count']} real, {stats['demo_leads_count']} demo)")
    print(f"  • Valid Email Addresses:   {stats['valid_emails']}")
    print(f"  • Business B2B Prospects:  {stats['business_contacts']}")
    print(f"  • Individual Contacts:     {stats['individual_contacts']}")
    print(f"  • Outreach Deliveries:     {stats['successful_deliveries']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resonance Singing Bowls Export Automation Pipeline")
    parser.add_argument("--keyword", type=str, default="Singing Bowls", help="Search keyword")
    parser.add_argument("--qualifiers", nargs="+", help="Intent qualifiers (e.g. wholesale distributor)")
    parser.add_argument("--sources", nargs="+", choices=["google", "facebook", "linkedin", "directory", "website"], help="Specific sources to query")
    parser.add_argument("--send", action="store_true", help="Trigger outreach dispatch")
    args = parser.parse_args()

    run_pipeline(keyword=args.keyword, qualifiers=args.qualifiers, sources=args.sources, run_outreach=args.send)
