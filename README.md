# Instantly 24h Reply Monitor

A Railway cron job that watches for positive replies in Instantly and sends a Slack notification if no staff member has replied within 24 hours.

## How it works

```
Every hour (Railway cron):
  1. Fetch all "Interested" leads from Instantly (paginated)
  2. Deduplicate by email address
  3. Filter to leads whose positive reply is 24–48h old
  4. For each: check the Unibox for an outbound staff reply
  5. If no reply found → send Slack notification
```

**Deduplication without a database:** The 24–48h window means each lead triggers exactly one notification cycle. No Redis or Postgres needed.

## Setup

### 1. Slack Incoming Webhook

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it `Instantly Reply Monitor`, pick your workspace
3. Go to **Incoming Webhooks** → toggle **Activate Incoming Webhooks** → ON
4. Click **Add New Webhook to Workspace** → pick the channel to post to
5. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`)

### 2. Deploy to Railway

1. Fork or clone this repo to your GitHub account
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select this repo
4. Go to **Variables** and add:

| Variable | Value |
|---|---|
| `INSTANTLY_API_KEY` | Your Instantly v2 API key |
| `SLACK_WEBHOOK_URL` | Your Slack webhook URL from step 1 |
| `DRY_RUN` | `true` (set to `false` when ready) |

5. Railway will detect `railway.json` and set up the cron automatically (runs every hour)

### 3. Test locally

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your values in .env
DRY_RUN=true python main.py
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `INSTANTLY_API_KEY` | required | Instantly v2 API key |
| `SLACK_WEBHOOK_URL` | required | Slack incoming webhook URL |
| `NOTIFY_AFTER_HOURS` | `24` | Hours before triggering a notification |
| `WINDOW_HOURS` | `24` | Notification window size (to avoid duplicates) |
| `DRY_RUN` | `false` | Log without sending Slack messages |
| `SEND_SLACK_SUMMARY` | `false` | Post a run summary to Slack after each check |

## Slack notification

Each alert looks like this:

```
⚠️ Unresponded Positive Reply
🟡 Follow up needed — over 24 hours

Lead:       john@restaurant.com
Campaign:   Restaurant Owners Q2
Waiting:    26.3 hours
Status:     No staff reply found

[ View in Instantly → ]
```

Urgency escalates automatically:
- 🟡 24–36h
- 🟠 36–48h  
- 🔴 48h+

## Adjusting the cron schedule

Edit `railway.json`:
```json
"cronSchedule": "0 * * * *"   // every hour (default)
"cronSchedule": "*/30 * * * *" // every 30 minutes
"cronSchedule": "0 */2 * * *"  // every 2 hours
```

## Notes

- The `type: "sent"` check in `has_staff_replied()` covers standard Unibox replies. If your Instantly account uses different type labels, adjust the list in `main.py` → `has_staff_replied()`.
- Leads with a null `timestamp_last_interest_change` fall back to `timestamp_last_reply`.
