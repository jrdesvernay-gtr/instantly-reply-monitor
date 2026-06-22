"""
Instantly 24h Reply Monitor
----------------------------
Runs as a Railway cron job (every hour by default).
Fetches all "Interested" leads from Instantly, finds ones where no staff
member has replied within NOTIFY_AFTER_HOURS (default 24h), and fires a
Slack notification for each.

Deduplication strategy (no database required):
  Only notify leads whose positive reply timestamp falls within the window:
    [now - (NOTIFY_AFTER_HOURS + WINDOW_HOURS), now - NOTIFY_AFTER_HOURS]
  Default: 24–48h window. This means each lead gets one Slack alert.
  If the cron runs hourly, each lead is caught once during its 24th hour.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

from instantly_client import InstantlyClient
from slack_client import SlackClient

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def has_staff_replied(emails: list[dict], after_ts_str: str) -> bool:
    """
    Return True if any email in the Unibox list is:
      - type == "sent" (outbound from staff)
      - created_at is after the lead's positive reply timestamp
    Adjust "sent" if your Instantly account uses a different type label.
    """
    for email in emails:
        email_type = email.get("type", "")
        created_at = email.get("created_at", "")

        is_outbound = email_type in ("sent", "reply_sent", "manual")
        is_after = created_at > after_ts_str  # ISO string comparison is valid for UTC

        if is_outbound and is_after:
            return True
    return False


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def run_check() -> None:
    # --- Config ---
    api_key = os.environ.get("INSTANTLY_API_KEY", "")
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    notify_after_hours = float(os.environ.get("NOTIFY_AFTER_HOURS", "24"))
    window_hours = float(os.environ.get("WINDOW_HOURS", "24"))
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    send_summary = os.environ.get("SEND_SLACK_SUMMARY", "false").lower() == "true"

    if not api_key or not slack_url:
        print("ERROR: INSTANTLY_API_KEY and SLACK_WEBHOOK_URL env vars are required.")
        sys.exit(1)

    if dry_run:
        print("⚠️  DRY RUN mode — Slack notifications will NOT be sent.\n")

    now = datetime.now(timezone.utc)
    notify_cutoff = now - timedelta(hours=notify_after_hours)       # older than this → notify
    window_start = now - timedelta(hours=notify_after_hours + window_hours)  # don't go further back

    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Starting 24h reply check")
    print(f"  Notification window: {notify_after_hours}–{notify_after_hours + window_hours}h old")

    instantly = InstantlyClient(api_key=api_key)
    slack = SlackClient(webhook_url=slack_url)

    # 1. Campaign name map
    print("\n→ Fetching campaigns...")
    campaign_map = instantly.get_campaign_map()
    print(f"  {len(campaign_map)} campaigns loaded")

    # 2. All interested leads
    print("\n→ Fetching interested leads...")
    all_leads = instantly.get_interested_leads()
    print(f"  {len(all_leads)} interested leads total")

    # 3. Dedupe by email (keep campaign-attributed record where possible)
    seen: dict[str, dict] = {}
    for lead in all_leads:
        email = lead.get("email", "")
        if not email:
            continue
        existing = seen.get(email)
        # Prefer records that have a real campaign + reply step
        if (
            not existing
            or (
                lead.get("campaign")
                and lead.get("email_replied_step")
                and not (existing.get("campaign") and existing.get("email_replied_step"))
            )
        ):
            seen[email] = lead
    deduped = list(seen.values())
    print(f"  {len(deduped)} unique leads after dedup")

    # 4. Filter to notification window
    stale: list[tuple[dict, datetime, str]] = []
    for lead in deduped:
        ts_str = lead.get("timestamp_last_interest_change") or lead.get("timestamp_last_reply")
        ts = parse_ts(ts_str)
        if not ts or not ts_str:
            continue
        if window_start <= ts <= notify_cutoff:
            stale.append((lead, ts, ts_str))

    print(f"\n→ Leads in notification window: {len(stale)}")

    if not stale:
        print("  Nothing to do.")
        if send_summary and not dry_run:
            slack.send_summary(total_stale=0, notified=0, checked=len(deduped))
        return

    # 5. Check Unibox for staff replies & notify
    notified = 0
    for lead, interest_ts, ts_str in stale:
        email = lead.get("email", "")
        campaign_id = lead.get("campaign", "")
        campaign_name = campaign_map.get(campaign_id, campaign_id or "Unknown Campaign")
        lead_id = lead.get("id", "")
        hours_waiting = (now - interest_ts).total_seconds() / 3600

        print(f"\n  Checking {email} ({hours_waiting:.1f}h)…")

        emails = instantly.get_emails_for_lead(email)
        if has_staff_replied(emails, ts_str):
            print(f"    ✓ Staff already replied — skipping")
            continue

        print(f"    ✗ No staff reply found")
        if not dry_run:
            slack.notify_unresponded_lead(
                email=email,
                campaign=campaign_name,
                hours_waiting=round(hours_waiting, 1),
                lead_id=lead_id,
            )
        else:
            print(f"    [DRY RUN] Would notify Slack for {email}")
        notified += 1

    print(f"\n✅ Done — notified for {notified}/{len(stale)} leads")

    if send_summary and not dry_run and notified > 0:
        slack.send_summary(total_stale=len(stale), notified=notified, checked=len(deduped))


if __name__ == "__main__":
    run_check()
