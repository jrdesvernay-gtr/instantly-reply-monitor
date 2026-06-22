"""
Slack Incoming Webhook client.
Sends a rich Block Kit notification for each unresponded positive reply.
"""

import json
import httpx


class SlackClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def notify_unresponded_lead(
        self,
        email: str,
        campaign: str,
        hours_waiting: float,
        lead_id: str = "",
    ) -> None:
        lead_url = (
            f"https://app.instantly.ai/app/leads/{lead_id}"
            if lead_id
            else "https://app.instantly.ai/app/unibox"
        )

        # Urgency label
        if hours_waiting >= 48:
            urgency = "🔴 *URGENT* — over 48 hours"
        elif hours_waiting >= 36:
            urgency = "🟠 *High priority* — over 36 hours"
        else:
            urgency = "🟡 *Follow up needed* — over 24 hours"

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚠️ Unresponded Positive Reply",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": urgency,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Lead:*\n`{email}`"},
                        {"type": "mrkdwn", "text": f"*Campaign:*\n{campaign}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Waiting since reply:*\n{hours_waiting:.1f} hours",
                        },
                        {"type": "mrkdwn", "text": "*Staff replied:*\nNo reply found"},
                    ],
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View in Instantly →",
                                "emoji": True,
                            },
                            "url": lead_url,
                            "style": "primary",
                        }
                    ],
                },
            ]
        }

        resp = httpx.post(
            self.webhook_url,
            content=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"  ✓ Notified Slack: {email} ({hours_waiting:.1f}h waiting)")

    def send_summary(self, total_stale: int, notified: int, checked: int) -> None:
        """Optional run summary posted to Slack."""
        if total_stale == 0:
            text = "✅ *24h reply check complete* — no unresponded leads found."
        else:
            text = (
                f"📋 *24h reply check complete* — "
                f"{notified}/{total_stale} unresponded leads notified "
                f"(checked {checked} interested leads total)."
            )

        resp = httpx.post(
            self.webhook_url,
            content=json.dumps({"text": text}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
