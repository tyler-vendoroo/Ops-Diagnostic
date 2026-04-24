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
              <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo</p>
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
                  <td width="50%" style="text-align:center;padding:24px;background-color:#039cac;border-radius:8px;">
                    <p style="margin:0;color:#b2ebf2;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Recommended Tier</p>
                    <p style="margin:8px 0 0;color:#ffffff;font-size:32px;font-weight:800;line-height:1;">{tier_display}</p>
                    <p style="margin:4px 0 0;color:#b2ebf2;font-size:13px;">Vendoroo plan</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Key Findings -->
          {"" if not findings_html else f'''
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 16px;color:#0F172A;font-size:16px;font-weight:700;border-bottom:2px solid #039cac;padding-bottom:8px;">Key Findings</h2>
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
                &copy; Vendoroo &bull; <a href="https://vendoroo.com" style="color:#039cac;text-decoration:none;">vendoroo.com</a>
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
              <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo — Sales Alert</p>
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
                    <a href="mailto:{lead_email}" style="color:#039cac;text-decoration:none;">{lead_email}</a>
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
                    <span style="display:inline-block;background-color:#039cac;color:#ffffff;font-size:12px;font-weight:700;padding:3px 10px;border-radius:4px;text-transform:uppercase;letter-spacing:0.05em;">{tier_display}</span>
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

    async def send_quick_diagnostic_results(
        self,
        lead_email: str,
        lead_name: str,
        diagnostic_id: str,
        overall_score: float,
        insights: list,
        category_scores: list,
        company_name: str,
        door_count: int,
        staff_count: int,
        staff_label: str,
        prefill_token: str,
    ) -> None:
        """Send quick diagnostic results email with insights and two CTAs."""
        try:
            score_int = int(overall_score)
            frontend_url = settings.frontend_url

            insight_icons = {
                "scale": "📊", "clock": "⏱", "vendors": "🔧",
                "moon": "🌙", "alert": "⚠️", "dollar": "💰", "target": "🎯",
            }

            insights_html = ""
            for ins in insights[:4]:
                icon = insight_icons.get(ins.get("icon", ""), "📋")
                title = ins.get("title", "")
                detail = ins.get("detail", "")
                insights_html += f"""
                <tr>
                  <td style="padding:16px 20px;border-bottom:1px solid #f1f5f9;">
                    <p style="margin:0 0 4px;font-size:14px;font-weight:600;color:#0F172A;">{icon} {title}</p>
                    <p style="margin:0;font-size:13px;color:#64748b;line-height:1.5;">{detail}</p>
                  </td>
                </tr>"""

            cats_html = ""
            for cat in category_scores[:5]:
                score = cat.get("score", 0)
                name = cat.get("name", "")
                tier_label = cat.get("tier", "")
                bar_color = "#22C55E" if score >= 70 else "#F59E0B" if score >= 50 else "#EF4444"
                tier_color = "#16A34A" if score >= 70 else "#CA8A04" if score >= 50 else "#DC2626"
                cats_html += f"""
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#334155;width:40%;">{name}</td>
                  <td style="padding:6px 8px;width:10%;text-align:right;font-size:13px;font-weight:700;color:#0F172A;">{score}</td>
                  <td style="padding:6px 0;width:35%;">
                    <div style="background:#f1f5f9;border-radius:4px;height:8px;overflow:hidden;">
                      <div style="background:{bar_color};height:100%;width:{score}%;border-radius:4px;"></div>
                    </div>
                  </td>
                  <td style="padding:6px 0 6px 12px;width:15%;text-align:right;font-size:11px;font-weight:600;color:{tier_color};">{tier_label}</td>
                </tr>"""

            import urllib.parse
            full_url = f"{frontend_url}/diagnostic/full?prefill={prefill_token}"
            results_url = f"{frontend_url}/diagnostic/results/{diagnostic_id}"
            book_call_url = f"{settings.frontend_url}/schedule"

            share_url = f"https://diagnostic.vendoroo.ai?ref={prefill_token}"
            share_url_encoded = urllib.parse.quote(share_url)
            _hashtags = "#PropertyManagement #PropTech #AIinRealEstate #MaintenanceOps #Vendoroo #NARPM #BrokerOwner2026"
            share_text = (
                "Did you know the average property manager takes over 4 hours to respond to a maintenance request? "
                f"Just ran a free ops diagnostic from @VendorooAI — eye-opening. Takes 2 minutes.\n\n{_hashtags}"
            )
            full_share = f"{share_text}\n\n{share_url}"
            full_share_encoded = urllib.parse.quote(full_share)
            linkedin_url = f"https://www.linkedin.com/feed/?shareActive=true&text={full_share_encoded}"
            twitter_url = f"https://twitter.com/intent/tweet?text={full_share_encoded}"
            facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={share_url_encoded}"

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <tr>
            <td style="background-color:#1a1a2e;padding:32px 40px;">
              <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo · AI Diagnostics</p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Your Operations Snapshot</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px 0;">
              <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {lead_name},</p>
              <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
                Here are your quick diagnostic results for {company_name} — {door_count} doors, {staff_count} {staff_label}.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="text-align:center;padding:32px;background-color:#1a1a2e;border-radius:12px;">
                    <p style="margin:0;color:#6b7280;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.15em;">Operations Snapshot</p>
                    <p style="margin:12px 0 0;color:#ffffff;font-size:56px;font-weight:800;line-height:1;">{score_int}</p>
                    <p style="margin:4px 0 0;color:#6b7280;font-size:13px;">out of 100</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 16px;color:#039cac;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">What we see in your operation</h2>
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #f1f5f9;border-radius:8px;overflow:hidden;">
                {insights_html}
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 12px;color:#0F172A;font-size:14px;font-weight:600;">Categories scored from your survey</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                {cats_html}
              </table>
              <p style="margin:12px 0 0;color:#94a3b8;font-size:12px;line-height:1.5;">
                3 additional categories — Documentation Quality, Policy Completeness, and Operational Consistency — require your actual files to score accurately.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="text-align:center;padding-bottom:12px;">
                    <a href="{full_url}" style="display:inline-block;background-color:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
                      Get your full data-driven analysis →
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="text-align:center;padding-bottom:12px;">
                    <a href="{book_call_url}" style="display:inline-block;color:#039cac;font-size:13px;font-weight:600;text-decoration:none;">
                      Book a meeting or come see us at Imperial Room 5A (4th floor)
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="text-align:center;">
                    <a href="{results_url}" style="color:#94a3b8;font-size:12px;text-decoration:none;">
                      View results online →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 40px;text-align:center;border-top:1px solid #f1f5f9;">
              <p style="margin:0 0 12px;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Share your results</p>
              <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 12px;">
                    <a href="{linkedin_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">LinkedIn</a>
                  </td>
                  <td style="padding:0 4px;color:#e2e8f0;">|</td>
                  <td style="padding:0 12px;">
                    <a href="{twitter_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">X</a>
                  </td>
                  <td style="padding:0 4px;color:#e2e8f0;">|</td>
                  <td style="padding:0 12px;">
                    <a href="{facebook_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">Facebook</a>
                  </td>
                  <td style="padding:0 4px;color:#e2e8f0;">|</td>
                  <td style="padding:0 12px;">
                    <a href="{results_url}?share=true" target="_blank" style="text-decoration:none;color:#94a3b8;font-size:13px;">More options</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:#1a1a2e;padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#475569;font-size:12px;">
                &copy; Vendoroo &bull; <a href="https://vendoroo.ai" style="color:#039cac;text-decoration:none;">vendoroo.ai</a>
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
                "subject": f"Your Vendoroo Operations Snapshot — Score: {score_int}/100",
                "html": html_body,
            }

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send(params)
            )
            logger.info(
                "Sent quick diagnostic email to %s (diagnostic %s)", lead_email, diagnostic_id
            )

        except Exception as exc:
            logger.error(
                "Failed to send quick diagnostic email to %s: %s", lead_email, exc
            )

    async def send_reminder_touch_1(
        self,
        lead_email: str,
        lead_name: str,
        diagnostic_id: str,
        overall_score: int,
        prefill_token: str,
    ) -> None:
        """Touch 1 (48hrs): Your score is waiting — here's what it's missing."""
        try:
            import urllib.parse
            frontend_url = settings.frontend_url
            full_url = f"{frontend_url}/diagnostic/full?prefill={prefill_token}"
            results_url = f"{frontend_url}/diagnostic/results/{diagnostic_id}"

            share_url = f"https://diagnostic.vendoroo.ai?ref={prefill_token}"
            share_url_encoded = urllib.parse.quote(share_url)
            _hashtags = "#PropertyManagement #PropTech #AIinRealEstate #MaintenanceOps #Vendoroo #NARPM #BrokerOwner2026"
            _share_text = (
                "Did you know the average property manager takes over 4 hours to respond to a maintenance request? "
                f"Just ran a free ops diagnostic from @VendorooAI — eye-opening. Takes 2 minutes.\n\n{_hashtags}"
            )
            _full_share = f"{_share_text}\n\n{share_url}"
            _full_share_encoded = urllib.parse.quote(_full_share)
            linkedin_url = f"https://www.linkedin.com/feed/?shareActive=true&text={_full_share_encoded}"
            twitter_url = f"https://twitter.com/intent/tweet?text={_full_share_encoded}"
            facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={share_url_encoded}"

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <tr><td style="background-color:#1a1a2e;padding:32px 40px;">
          <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo · AI Diagnostics</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:20px;font-weight:700;">Your operations score is waiting for the full picture</h1>
        </td></tr>
        <tr><td style="padding:32px 40px;">
          <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {lead_name},</p>
          <p style="margin:0 0 16px;color:#64748b;font-size:14px;line-height:1.6;">
            You scored <strong style="color:#0F172A;">{overall_score}/100</strong> on your quick diagnostic. But 3 categories — Documentation Quality, Policy Completeness, and Operational Consistency — couldn't be scored accurately without your actual data.
          </p>
          <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
            Upload your work order history and we'll show you the complete picture — real response times, vendor performance, and specific gaps with remediation plans.
          </p>
          <p style="text-align:center;margin:0 0 16px;">
            <a href="{full_url}" style="display:inline-block;background-color:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
              Complete your full diagnostic →
            </a>
          </p>
          <p style="text-align:center;margin:0;">
            <a href="{results_url}" style="color:#94a3b8;font-size:12px;text-decoration:none;">View your quick results →</a>
          </p>
        </td></tr>
        <tr><td style="padding:16px 40px;text-align:center;border-top:1px solid #f1f5f9;">
          <p style="margin:0 0 12px;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Share your results</p>
          <table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>
            <td style="padding:0 12px;"><a href="{linkedin_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">LinkedIn</a></td>
            <td style="padding:0 4px;color:#e2e8f0;">|</td>
            <td style="padding:0 12px;"><a href="{twitter_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">X</a></td>
            <td style="padding:0 4px;color:#e2e8f0;">|</td>
            <td style="padding:0 12px;"><a href="{facebook_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">Facebook</a></td>
            <td style="padding:0 4px;color:#e2e8f0;">|</td>
            <td style="padding:0 12px;"><a href="{results_url}?share=true" target="_blank" style="text-decoration:none;color:#94a3b8;font-size:13px;">More options</a></td>
          </tr></table>
        </td></tr>
        <tr><td style="background-color:#1a1a2e;padding:20px 40px;text-align:center;">
          <p style="margin:0;color:#475569;font-size:12px;">&copy; Vendoroo &bull; <a href="https://vendoroo.ai" style="color:#039cac;text-decoration:none;">vendoroo.ai</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send({
                    "from": settings.diagnostic_from_email,
                    "to": [lead_email],
                    "subject": "Your ops score is waiting — here's what it's missing",
                    "html": html_body,
                })
            )
            logger.info("Sent reminder touch 1 to %s", lead_email)
        except Exception as exc:
            logger.error("Reminder touch 1 failed for %s: %s", lead_email, exc)

    async def send_reminder_touch_2(
        self,
        lead_email: str,
        lead_name: str,
        diagnostic_id: str,
        overall_score: int,
        prefill_token: str,
    ) -> None:
        """Touch 2 (7 days): One file. 5 minutes. Complete picture."""
        try:
            import urllib.parse
            frontend_url = settings.frontend_url
            full_url = f"{frontend_url}/diagnostic/full?prefill={prefill_token}"

            share_url = f"https://diagnostic.vendoroo.ai?ref={prefill_token}"
            share_url_encoded = urllib.parse.quote(share_url)
            _hashtags = "#PropertyManagement #PropTech #AIinRealEstate #MaintenanceOps #Vendoroo #NARPM #BrokerOwner2026"
            _share_text = (
                "Did you know the average property manager takes over 4 hours to respond to a maintenance request? "
                f"Just ran a free ops diagnostic from @VendorooAI — eye-opening. Takes 2 minutes.\n\n{_hashtags}"
            )
            _full_share = f"{_share_text}\n\n{share_url}"
            _full_share_encoded = urllib.parse.quote(_full_share)
            linkedin_url = f"https://www.linkedin.com/feed/?shareActive=true&text={_full_share_encoded}"
            twitter_url = f"https://twitter.com/intent/tweet?text={_full_share_encoded}"
            facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={share_url_encoded}"

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <tr><td style="background-color:#1a1a2e;padding:32px 40px;">
          <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo · AI Diagnostics</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:20px;font-weight:700;">One file. Five minutes. The full picture.</h1>
        </td></tr>
        <tr><td style="padding:32px 40px;">
          <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {lead_name},</p>
          <p style="margin:0 0 16px;color:#64748b;font-size:14px;line-height:1.6;">
            Your quick diagnostic scored <strong style="color:#0F172A;">{overall_score}/100</strong>, but that's an estimate. Your actual work order data tells the real story — response times, vendor performance, completion rates, and gaps that are specific to your operation.
          </p>
          <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
            Export your work order history from your PMS (12 months recommended), upload it, and we'll do the rest. Takes about 5 minutes.
          </p>
          <p style="text-align:center;margin:0;">
            <a href="{full_url}" style="display:inline-block;background-color:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
              Upload your work orders →
            </a>
          </p>
        </td></tr>
        <tr><td style="padding:16px 40px;text-align:center;border-top:1px solid #f1f5f9;">
          <p style="margin:0 0 12px;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Share your results</p>
          <table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>
            <td style="padding:0 12px;"><a href="{linkedin_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">LinkedIn</a></td>
            <td style="padding:0 4px;color:#e2e8f0;">|</td>
            <td style="padding:0 12px;"><a href="{twitter_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">X</a></td>
            <td style="padding:0 4px;color:#e2e8f0;">|</td>
            <td style="padding:0 12px;"><a href="{facebook_url}" target="_blank" style="text-decoration:none;color:#039cac;font-size:13px;font-weight:600;">Facebook</a></td>
          </tr></table>
        </td></tr>
        <tr><td style="background-color:#1a1a2e;padding:20px 40px;text-align:center;">
          <p style="margin:0;color:#475569;font-size:12px;">&copy; Vendoroo &bull; <a href="https://vendoroo.ai" style="color:#039cac;text-decoration:none;">vendoroo.ai</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send({
                    "from": settings.diagnostic_from_email,
                    "to": [lead_email],
                    "subject": "One file. Five minutes. Your complete ops analysis.",
                    "html": html_body,
                })
            )
            logger.info("Sent reminder touch 2 to %s", lead_email)
        except Exception as exc:
            logger.error("Reminder touch 2 failed for %s: %s", lead_email, exc)

    async def send_reminder_touch_3(
        self,
        lead_email: str,
        lead_name: str,
        book_call_url: str = f"{settings.frontend_url}/schedule",
    ) -> None:
        """Touch 3 (14 days): Pivot to a call. No more diagnostic push."""
        try:
            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <tr><td style="background-color:#1a1a2e;padding:32px 40px;">
          <p style="margin:0;color:#039cac;font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:20px;font-weight:700;">Want us to walk you through your results?</h1>
        </td></tr>
        <tr><td style="padding:32px 40px;">
          <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {lead_name},</p>
          <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
            We know things get busy. If you'd rather have one of our team walk you through your diagnostic results and answer any questions, we're happy to set up a quick call. No prep needed — we already have your data.
          </p>
          <p style="text-align:center;margin:0;">
            <a href="{book_call_url}" style="display:inline-block;background-color:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
              Book a meeting or come see us at Imperial Room 5A (4th floor)
            </a>
          </p>
        </td></tr>
        <tr><td style="background-color:#1a1a2e;padding:20px 40px;text-align:center;">
          <p style="margin:0;color:#475569;font-size:12px;">&copy; Vendoroo &bull; <a href="https://vendoroo.ai" style="color:#039cac;text-decoration:none;">vendoroo.ai</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: resend.Emails.send({
                    "from": settings.diagnostic_from_email,
                    "to": [lead_email],
                    "subject": "Want us to walk you through your results?",
                    "html": html_body,
                })
            )
            logger.info("Sent reminder touch 3 to %s", lead_email)
        except Exception as exc:
            logger.error("Reminder touch 3 failed for %s: %s", lead_email, exc)
