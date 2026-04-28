"""
Shared email-sending service.

Used for OTP delivery and post-scan report emails. Centralises SMTP/TLS
configuration so callers don't have to deal with certifi/ssl context setup.
"""

from __future__ import annotations

import ssl
from email.message import EmailMessage
from typing import Optional

import aiosmtplib
import certifi

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()


def _build_tls_context() -> ssl.SSLContext:
    """SSL context using certifi's CA bundle (works on macOS Python builds)."""
    return ssl.create_default_context(cafile=certifi.where())


async def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure.

    Never raises — callers can fire-and-forget without breaking the API path.
    """
    if not _settings.SMTP_USER or not _settings.SMTP_PASSWORD:
        logger.warning("email.smtp_not_configured", to=to)
        return False

    msg = EmailMessage()
    msg["From"] = _settings.SMTP_FROM or _settings.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=_settings.SMTP_HOST,
            port=_settings.SMTP_PORT,
            username=_settings.SMTP_USER,
            password=_settings.SMTP_PASSWORD,
            start_tls=True,
            tls_context=_build_tls_context(),
        )
        logger.info("email.sent", to=to, subject=subject)
        return True
    except Exception as exc:
        logger.error("email.send_failed", to=to, error=str(exc))
        return False


def _threat_color(level: str) -> str:
    return {
        "critical": "#dc2626",
        "high": "#ea580c",
        "medium": "#ca8a04",
        "low": "#16a34a",
    }.get((level or "low").lower(), "#64748b")


def build_scan_report_email(
    *,
    user_name: str,
    scan_type: str,
    source_label: str,
    threat_score: float,
    threat_level: str,
    summary: str,
    keywords: Optional[list] = None,
    model_used: Optional[str] = None,
) -> tuple[str, str, str]:
    """Build (subject, plain_text, html) for a scan report email."""
    keywords = keywords or []
    color = _threat_color(threat_level)
    score_pct = f"{round(float(threat_score or 0.0) * 100, 1)}%"
    level_upper = (threat_level or "low").upper()

    subject = f"TDM Scan Report — {level_upper} threat ({score_pct})"

    kw_text = ", ".join(str(k) for k in keywords[:10]) if keywords else "—"
    model_line = f"Model: {model_used}\n" if model_used else ""

    plain = (
        f"Hello {user_name},\n\n"
        f"Your {scan_type} scan has completed.\n\n"
        f"Source: {source_label}\n"
        f"Threat level: {level_upper}\n"
        f"Threat score: {score_pct}\n"
        f"{model_line}"
        f"\nSummary:\n{summary}\n\n"
        f"Top keywords: {kw_text}\n\n"
        f"— TDM Threat Detection & Monitoring\n"
    )

    kw_html = (
        "".join(
            f'<span style="display:inline-block;background:#f1f5f9;color:#0f172a;'
            f'padding:2px 8px;margin:2px;border-radius:4px;font-size:12px;">{k}</span>'
            for k in keywords[:10]
        )
        if keywords
        else '<span style="color:#94a3b8;">—</span>'
    )

    html = f"""\
<!DOCTYPE html>
<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
    <div style="background:{color};color:#ffffff;padding:16px 20px;">
      <h2 style="margin:0;font-size:18px;">TDM Scan Report</h2>
      <p style="margin:4px 0 0;font-size:13px;opacity:0.95;">Threat level: <strong>{level_upper}</strong> &middot; Score: <strong>{score_pct}</strong></p>
    </div>
    <div style="padding:20px;">
      <p style="margin:0 0 12px;">Hello <strong>{user_name}</strong>,</p>
      <p style="margin:0 0 16px;">Your {scan_type} scan has completed. Details below.</p>

      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:16px;">
        <tr><td style="padding:6px 0;color:#64748b;width:120px;">Source</td><td style="padding:6px 0;">{source_label}</td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Threat level</td><td style="padding:6px 0;"><strong style="color:{color};">{level_upper}</strong></td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Threat score</td><td style="padding:6px 0;">{score_pct}</td></tr>
        {f'<tr><td style="padding:6px 0;color:#64748b;">Model</td><td style="padding:6px 0;">{model_used}</td></tr>' if model_used else ''}
      </table>

      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin-bottom:16px;">
        <div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Summary</div>
        <div style="font-size:14px;line-height:1.5;white-space:pre-wrap;">{summary}</div>
      </div>

      <div style="margin-bottom:8px;">
        <div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Top keywords</div>
        <div>{kw_html}</div>
      </div>
    </div>
    <div style="background:#f8fafc;color:#94a3b8;font-size:11px;padding:12px 20px;border-top:1px solid #e2e8f0;">
      TDM Threat Detection &amp; Monitoring &middot; automated report
    </div>
  </div>
</body></html>"""

    return subject, plain, html
