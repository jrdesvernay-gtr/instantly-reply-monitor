"""
Resend email notification client.
Replaces slack_client.py — sends HTML email alerts for unresponded positive replies.
"""

import httpx
import json


class EmailClient:
    RESEND_API = "https://api.resend.com/emails"

    def __init__(self, api_key: str, from_email: str, to_email: str):
        self.api_key = api_key
        self.from_email = from_email
        self.to_email = to_email

    def _send(self, subject: str, html: str) -> None:
        resp = httpx.post(
            self.RESEND_API,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            content=json.dumps({
                "from": self.from_email,
                "to": [self.to_email],
                "subject": subject,
                "html": html,
            }),
            timeout=15,
        )
        resp.raise_for_status()

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

        if hours_waiting >= 48:
            urgency_color = "#dc2626"
            urgency_label = "🔴 URGENT — over 48 hours"
        elif hours_waiting >= 36:
            urgency_color = "#ea580c"
            urgency_label = "🟠 High priority — over 36 hours"
        else:
            urgency_color = "#ca8a04"
            urgency_label = "🟡 Follow up needed — over 24 hours"

        subject = f"⚠️ Unresponded reply: {email} ({hours_waiting:.0f}h waiting)"

        html = f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <div style="background:#18181b;border-radius:8px;padding:24px;color:#fff;">
            <h2 style="margin:0 0 4px;font-size:18px;">⚠️ Unresponded Positive Reply</h2>
            <p style="margin:0 0 20px;color:{urgency_color};font-weight:600;">{urgency_label}</p>
            <table style="width:100%;border-collapse:collapse;">
              <tr>
                <td style="padding:8px 0;color:#a1a1aa;font-size:13px;width:140px;">Lead</td>
                <td style="padding:8px 0;font-size:13px;font-weight:600;">{email}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Campaign</td>
                <td style="padding:8px 0;font-size:13px;">{campaign}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Waiting</td>
                <td style="padding:8px 0;font-size:13px;">{hours_waiting:.1f} hours</td>
              </tr>
              <tr>
                <td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Staff replied</td>
                <td style="padding:8px 0;font-size:13px;color:#f87171;">No reply found</td>
              </tr>
            </table>
            <a href="{lead_url}"
               style="display:inline-block;margin-top:20px;padding:10px 20px;
                      background:#2563eb;color:#fff;border-radius:6px;
                      text-decoration:none;font-size:14px;font-weight:600;">
              View in Instantly →
            </a>
          </div>
        </div>
        """

        self._send(subject=subject, html=html)
        print(f"  ✓ Email sent for {email} ({hours_waiting:.1f}h waiting)")

    def send_summary(self, total_stale: int, notified: int, checked: int) -> None:
        if total_stale == 0:
            subject = "✅ 24h reply check — all clear"
            body = f"<p>Checked <strong>{checked}</strong> interested leads. No unresponded replies found.</p>"
        else:
            subject = f"📋 24h reply check — {notified} leads notified"
            body = f"""
            <p>Checked <strong>{checked}</strong> interested leads.<br>
            Notified for <strong>{notified}/{total_stale}</strong> unresponded leads.</p>
            """

        html = f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <div style="background:#18181b;border-radius:8px;padding:24px;color:#fff;">
            <h2 style="margin:0 0 16px;font-size:18px;">{subject}</h2>
            <div style="color:#d4d4d8;font-size:14px;">{body}</div>
          </div>
        </div>
        """
        self._send(subject=subject, html=html)
