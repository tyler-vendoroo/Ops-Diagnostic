"""Notification service: Slack + sales email for high-intent prospect signals."""

import asyncio
import hashlib
import logging
import os

import httpx
import resend

from app.config import settings

logger = logging.getLogger(__name__)

_INTEREST_SECRET = "vendoroo_interest"
_SALES_EMAILS = ["tyler@vendoroo.ai", "shayna@vendoroo.ai"]


def generate_interest_token(lead_id: str) -> str:
    return hashlib.sha256(f"{lead_id}{_INTEREST_SECRET}".encode()).hexdigest()[:16]


def verify_interest_token(lead_id: str, token: str) -> bool:
    return generate_interest_token(lead_id) == token


async def send_interest_notifications(lead_data: dict) -> None:
    """Fire Slack + sales email concurrently. Both fail silently."""
    await asyncio.gather(
        _send_slack(lead_data),
        _send_sales_email(lead_data),
        return_exceptions=True,
    )


async def _send_slack(lead_data: dict) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        payload = {
            "text": f"🔥 *{lead_data.get('company', 'Unknown')}* wants to move forward!",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🔥 {lead_data.get('company', 'Unknown')} wants to move forward!"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Contact:* {lead_data.get('name', '—')}"},
                        {"type": "mrkdwn", "text": f"*Email:* {lead_data.get('email', '—')}"},
                        {"type": "mrkdwn", "text": f"*Doors:* {lead_data.get('door_count', '—')}"},
                        {"type": "mrkdwn", "text": f"*Score:* {lead_data.get('score', '—')}/100"},
                        {"type": "mrkdwn", "text": f"*Goal:* {lead_data.get('goal', '—')}"},
                        {"type": "mrkdwn", "text": f"*Top Gap:* {lead_data.get('top_gap', '—')}"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View in Dashboard"},
                            "url": lead_data.get("dashboard_url", f"{settings.frontend_url}/internal"),
                        }
                    ],
                },
            ],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json=payload)
        logger.info("Slack notification sent for %s", lead_data.get("email"))
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)


async def _send_sales_email(lead_data: dict) -> None:
    if not settings.resend_api_key:
        return
    try:
        resend.api_key = settings.resend_api_key
        name = lead_data.get("name", "Unknown")
        company = lead_data.get("company", "Unknown")
        email = lead_data.get("email", "")
        door_count = lead_data.get("door_count", "—")
        score = lead_data.get("score", "—")
        staff_count = lead_data.get("staff_count", "—")
        model = lead_data.get("operational_model", "")
        goal = lead_data.get("goal", "—")
        top_gap = lead_data.get("top_gap", "—")
        gap_count = lead_data.get("gap_count", "—")
        dashboard_url = lead_data.get("dashboard_url", "")
        results_url = lead_data.get("results_url", "")

        results_btn = (
            f'<a href="{results_url}" style="display:inline-block;background:#0F172A;color:white;'
            f'font-size:13px;font-weight:600;padding:10px 20px;border-radius:8px;text-decoration:none;">View Results</a>'
        ) if results_url else ""

        html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:560px;margin:0 auto;padding:32px;">
  <div style="background:#1a1a2e;padding:20px 28px;border-radius:10px 10px 0 0;">
    <h2 style="margin:0;color:#FDBB00;font-size:18px;">&#128293; {company} wants to move forward</h2>
  </div>
  <div style="background:white;padding:24px 28px;border:1px solid #f1f5f9;border-top:none;border-radius:0 0 10px 10px;">
    <p style="margin:0 0 16px;color:#334155;font-size:14px;">
      <strong>{name}</strong> from <strong>{company}</strong> clicked &ldquo;I want to move forward.&rdquo;
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px;">
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;width:120px;">Score</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{score}/100</td>
      </tr>
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;">Doors</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{door_count}</td>
      </tr>
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;">Staff</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{staff_count} {model}</td>
      </tr>
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;">Goal</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{goal}</td>
      </tr>
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;">Top Gap</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{top_gap}</td>
      </tr>
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:7px 0;color:#64748b;">Gap Count</td>
        <td style="padding:7px 0;font-weight:600;color:#0F172A;">{gap_count}</td>
      </tr>
      <tr>
        <td style="padding:7px 0;color:#64748b;">Email</td>
        <td style="padding:7px 0;font-weight:600;color:#039cac;">{email}</td>
      </tr>
    </table>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <a href="{dashboard_url}" style="display:inline-block;background:#039cac;color:white;font-size:13px;font-weight:600;padding:10px 20px;border-radius:8px;text-decoration:none;">View in Dashboard</a>
      {results_btn}
    </div>
    <p style="margin:20px 0 0;color:#EF4444;font-size:13px;font-weight:700;">&#9889; Reach out within 24 hours.</p>
  </div>
</div>"""

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: resend.Emails.send({
                "from": settings.diagnostic_from_email,
                "to": _SALES_EMAILS,
                "subject": f"\U0001f525 {company} wants to move forward — {door_count} doors",
                "html": html,
            }),
        )
        logger.info("Sales interest notification sent for %s", email)
    except Exception as exc:
        logger.warning("Sales interest email failed: %s", exc)
