"""
Instantly v2 API client.
Handles lead fetching, campaign lookup, and Unibox email retrieval.
"""

import httpx
from typing import Optional


class InstantlyClient:
    BASE_URL = "https://api.instantly.ai/api/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def get_campaign_map(self) -> dict[str, str]:
        """Return {campaign_id: campaign_name} for all campaigns."""
        campaigns: dict[str, str] = {}
        starting_after: Optional[str] = None

        while True:
            payload: dict = {"limit": 100}
            if starting_after:
                payload["starting_after"] = starting_after

            resp = httpx.post(
                f"{self.BASE_URL}/campaigns/list",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for c in data.get("items", []):
                campaigns[c["id"]] = c.get("name", c["id"])

            next_cursor = data.get("next_starting_after")
            if not next_cursor or len(data.get("items", [])) < 100:
                break
            starting_after = next_cursor

        return campaigns

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    def get_interested_leads(self) -> list[dict]:
        """
        Fetch all leads with lt_interest_status = Interested (FILTER_LEAD_INTERESTED),
        paginated across all pages.
        """
        leads: list[dict] = []
        starting_after: Optional[str] = None

        while True:
            payload: dict = {"filter": "FILTER_LEAD_INTERESTED", "limit": 100}
            if starting_after:
                payload["starting_after"] = starting_after

            resp = httpx.post(
                f"{self.BASE_URL}/leads/list",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            leads.extend(items)

            next_cursor = data.get("next_starting_after")
            if not next_cursor or len(items) < 100:
                break
            starting_after = next_cursor

        return leads

    # ------------------------------------------------------------------
    # Unibox emails
    # ------------------------------------------------------------------

    def get_emails_for_lead(self, lead_email: str) -> list[dict]:
        """
        Fetch Unibox emails for a specific lead email address.
        Returns a list of email objects; each has:
          - type: "sent" (outbound / staff reply) | "received" (inbound from lead)
          - created_at: ISO timestamp
          - subject, body, etc.
        """
        try:
            resp = httpx.post(
                f"{self.BASE_URL}/emails/list",
                headers=self.headers,
                json={"lead_email": lead_email, "limit": 50},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])
        except httpx.HTTPStatusError as e:
            print(f"  [warn] Could not fetch emails for {lead_email}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"  [warn] Could not fetch emails for {lead_email}: {e}")
            return []
