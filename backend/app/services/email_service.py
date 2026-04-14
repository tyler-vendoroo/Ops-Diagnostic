"""EmailService: sends diagnostic result emails and sales notifications via Resend."""

import asyncio
import logging
import base64

import resend

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends diagnostic result emails and sales notifications via Resend."""

    def __init__(self):
        resend.api_key = settings.resend_api_key

    async def send_diagnostic_results(
        self,
        lead_email: str,
        lead_name: str,
        diagnostic_id: str,
        overall_score: float,
        tier: str,
        key_findings: list,
        pdf_bytes: bytes | None,
    ) -> None:
        """Send results email to the user. Attach PDF if available."""
        try:
            tier_display = tier.capitalize()
            score_int = int(overall_score)

            # Top 3 findings as bulleted list
            top_findings = key_findings[:3]
            findings_html = ""
            for finding in top_findings:
                title = finding.get("title", "") if isinstance(finding, dict) else str(finding)
                detail = finding.get("detail", "") if isinstance(finding, dict) else ""
                findings_html += f"<li style='margin-bottom:8px;'><strong>{title}</strong>"
                if detail:
                    findings_html += f" — {detail}"
                findings_html += "</li>"

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="background-color:#0F172A;padding:32px 40px;">
              <p style="margin:0;color:#6366F1;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo</p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Operations Diagnostic Results</h1>
            </td>
          </tr>
          <!-- Score section -->
          <tr>
            <td style="padding:40px 40px 0;">
              <p style="margin:0 0 8px;color:#64748b;font-size:14px;">Hi {lead_name},</p>
              <p style="margin:0 0 32px;color:#334155;font-size:15px;line-height:1.6;">
                Your Vendoroo Operations Diagnostic is complete. Here's a summary of your results.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="50%" style="text-align:center;padding:24px;background-color:#f8fafc;border-radius:8px;">
                    <p style="margin:0;color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Overall Score</p>
                    <p style="margin:8px 0 0;color:#0F172A;font-size:56px;font-weight:800;line-height:1;">{score_int}</p>
                    <p style="margin:4px 0 0;color:#64748b;font-size:13px;">out of 100</p>
                  </td>
                  <td width="8"></td>
                  <td width="50%" style="text-align:center;padding:24px;background-color:#6366F1;border-radius:8px;">
                    <p style="margin:0;color:#c7d2fe;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Recommended Tier</p>
                    <p style="margin:8px 0 0;color:#ffffff;font-size:32px;font-weight:800;line-height:1;">{tier_display}</p>
                    <p style="margin:4px 0 0;color:#c7d2fe;font-size:13px;">Vendoroo plan</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Key Findings -->
          {"" if not findings_html else f'''
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 16px;color:#0F172A;font-size:16px;font-weight:700;border-bottom:2px solid #6366F1;padding-bottom:8px;">Key Findings</h2>
              <ul style="margin:0;padding-left:20px;color:#334155;font-size:14px;line-height:1.7;">
                {findings_html}
              </ul>
            </td>
          </tr>'''}
          <!-- CTA -->
          <tr>
            <td style="padding:32px 40px 40px;">
              <p style="margin:0 0 24px;color:#334155;font-size:14px;line-height:1.6;">
                A member of our team will be in touch to walk you through these results and answer any questions.
                {' Your full diagnostic report is attached as a PDF.' if pdf_bytes else ''}
              </p>
              <p style="margin:0;color:#94a3b8;font-size:12px;">
                This report was generated for diagnostic ID <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:11px;">{diagnostic_id}</code>.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color:#0F172A;padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#475569;font-size:12px;">
                &copy; Vendoroo &bull; <a href="https://vendoroo.com" style="color:#6366F1;text-decoration:none;">vendoroo.com</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            params: dict = {
                "from": settings.diagnostic_from_email,
                "to": [lead_email],
                "subject": "Your Vendoroo Operations Diagnostic Results",
                "html": html_body,
            }

            if pdf_bytes is not None:
                params["attachments"] = [
                    {
                        "filename": "diagnostic_report.pdf",
                        "content": list(pdf_bytes),
                    }
                ]

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send(params)
            )
            logger.info("Sent diagnostic results email to %s (diagnostic %s)", lead_email, diagnostic_id)

        except Exception as exc:
            logger.error(
                "Failed to send diagnostic results email to %s: %s",
                lead_email,
                exc,
            )

    async def send_sales_notification(
        self,
        lead_name: str,
        lead_email: str,
        lead_company: str,
        overall_score: float,
        tier: str,
    ) -> None:
        """Notify the sales team of a newly completed diagnostic."""
        try:
            tier_display = tier.capitalize()
            score_int = int(overall_score)

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <tr>
            <td style="background-color:#0F172A;padding:24px 32px;">
              <p style="margin:0;color:#6366F1;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo — Sales Alert</p>
              <h1 style="margin:6px 0 0;color:#ffffff;font-size:18px;font-weight:700;">New Diagnostic Completed</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                  <td style="padding:10px 12px;background-color:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:13px;color:#64748b;font-weight:600;width:35%;">Name</td>
                  <td style="padding:10px 12px;background-color:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:14px;color:#0F172A;">{lead_name}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#64748b;font-weight:600;">Email</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-size:14px;color:#0F172A;">
                    <a href="mailto:{lead_email}" style="color:#6366F1;text-decoration:none;">{lead_email}</a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;background-color:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:13px;color:#64748b;font-weight:600;">Company</td>
                  <td style="padding:10px 12px;background-color:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:14px;color:#0F172A;">{lead_company}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#64748b;font-weight:600;">Overall Score</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-size:14px;color:#0F172A;font-weight:700;">{score_int} / 100</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;background-color:#f8fafc;font-size:13px;color:#64748b;font-weight:600;">Recommended Tier</td>
                  <td style="padding:10px 12px;background-color:#f8fafc;">
                    <span style="display:inline-block;background-color:#6366F1;color:#ffffff;font-size:12px;font-weight:700;padding:3px 10px;border-radius:4px;text-transform:uppercase;letter-spacing:0.05em;">{tier_display}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:#0F172A;padding:16px 32px;text-align:center;">
              <p style="margin:0;color:#475569;font-size:12px;">&copy; Vendoroo Internal &bull; Sales Notification</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            subject = f"New Diagnostic: {lead_name} ({lead_company}) — Score: {overall_score:.0f}"

            params: dict = {
                "from": settings.diagnostic_from_email,
                "to": [settings.sales_notification_email],
                "subject": subject,
                "html": html_body,
            }

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send(params)
            )
            logger.info(
                "Sent sales notification for lead %s (%s), score %s",
                lead_email,
                lead_company,
                overall_score,
            )

        except Exception as exc:
            logger.error(
                "Failed to send sales notification for lead %s: %s",
                lead_email,
                exc,
            )
