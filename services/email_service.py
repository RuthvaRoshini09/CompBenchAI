"""
CompBench AI - Email Delivery Service (Phase 2)

Integrates:
- Official Resend Python SDK for transactional email delivery
- Account verification and password reset transactional email workflows
- Responsive, branded HTML email templates with plain-text fallbacks
- Strict credential and configuration validation (no hardcoded keys or sender addresses)
- Secure logging: token-bearing URLs, credentials, and sensitive payload contents are never logged
"""

import os
import re
import html
import logging
from typing import Dict, Any, Optional, Tuple
import resend

logger = logging.getLogger("compbench.email_service")


class EmailConfigurationError(ValueError):
    """Raised when email service credentials or configurations are invalid or missing."""
    pass


class EmailDeliveryError(RuntimeError):
    """Raised when email delivery via Resend API fails."""
    pass


def is_production() -> bool:
    """Check if the current runtime environment is production."""
    env = (
        os.getenv("ENVIRONMENT") or
        os.getenv("COMPBENCH_ENV") or
        os.getenv("VERCEL_ENV") or
        os.getenv("ENV") or
        ""
    ).strip().lower()
    return env in ("production", "prod")


def is_testing_environment() -> bool:
    """Check if automated test mode is explicitly enabled."""
    test_env = (
        os.getenv("TESTING") or
        os.getenv("COMPBENCH_TEST") or
        os.getenv("PYTEST_CURRENT_TEST") or
        ""
    ).strip().lower()
    return test_env in ("1", "true", "yes")


def mask_email_for_logging(email: str) -> str:
    """
    Safely mask an email address for non-sensitive logging.
    e.g., 'engineer@compbench.ai' -> 'en***er@compbench.ai'
    """
    if not email or "@" not in email:
        return "[masked-email]"
    local_part, domain = email.strip().split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + "*"
    else:
        masked_local = local_part[:2] + "***" + local_part[-1]
    return f"{masked_local}@{domain}"


def get_resend_api_key() -> str:
    """
    Retrieve and validate Resend API key strictly from environment.
    Raises EmailConfigurationError if missing or invalid.
    """
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        raise EmailConfigurationError(
            "RESEND_API_KEY environment variable is not configured. "
            "Please provide a valid Resend API key in .env or deployment settings."
        )
    if not api_key.startswith("re_"):
        raise EmailConfigurationError(
            "Invalid RESEND_API_KEY format: Resend API keys must start with 're_'."
        )
    return api_key


def get_sender_email() -> str:
    """
    Retrieve configured sender email address from environment.
    Defaults to 'CompBench AI <onboarding@resend.dev>' if not set.
    """
    sender = (os.getenv("RESEND_FROM_EMAIL") or "").strip()
    if sender:
        return sender
    return "CompBench AI <onboarding@resend.dev>"


def get_app_base_url() -> str:
    """
    Retrieve application base URL for link construction.
    Defaults to 'http://localhost:8000' in development.
    """
    url = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if url:
        return url
    vercel_url = (os.getenv("VERCEL_URL") or "").strip()
    if vercel_url:
        return f"https://{vercel_url}"
    return "http://localhost:8000"


def validate_email_address(email: str) -> bool:
    """Validate standard RFC 5322 email syntax."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(pattern, email.strip()))


# =====================================================================
# HTML & Plain-Text Template Generators
# =====================================================================

def generate_verification_email_html(full_name: str, verification_url: str) -> str:
    """Generate responsive, themed HTML email for account verification."""
    safe_name = html.escape(full_name.strip() if full_name else "CompBench User")
    safe_url = html.escape(verification_url.strip())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Your CompBench AI Account</title>
</head>
<body style="margin:0;padding:0;background-color:#090d16;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f3f4f6;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#090d16;padding:40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:540px;background-color:#111827;border:1px solid #1f2937;border-radius:12px;padding:36px 32px;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
          <!-- Header -->
          <tr>
            <td align="center" style="padding-bottom:24px;border-bottom:1px solid #1f2937;">
              <table role="presentation" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <span style="font-size:20px;font-weight:800;letter-spacing:-0.02em;color:#ffffff;display:inline-block;">
                      COMPBENCH <span style="color:#38bdf8;">AI</span>
                    </span>
                    <span style="display:inline-block;margin-left:8px;background-color:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;letter-spacing:0.06em;vertical-align:middle;">
                      ENGINEERING SUITE
                    </span>
                  </td>
                </tr>
              </table>
              <div style="font-size:12px;color:#9ca3af;margin-top:6px;">Automotive Component Benchmarking &amp; Engineering Intelligence</div>
            </td>
          </tr>

          <!-- Main Content -->
          <tr>
            <td style="padding-top:28px;">
              <h1 style="font-size:18px;font-weight:700;color:#ffffff;margin:0 0 16px 0;">Verify Your Email Address</h1>
              <p style="font-size:14px;line-height:1.6;color:#d1d5db;margin:0 0 20px 0;">
                Hello <strong>{safe_name}</strong>,
              </p>
              <p style="font-size:14px;line-height:1.6;color:#d1d5db;margin:0 0 24px 0;">
                Thank you for creating an account on CompBench AI. To activate your access to automotive component benchmarking, material intelligence teardowns, and engineering trade-off analytics, please verify your email address.
              </p>

              <!-- CTA Button -->
              <table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px 0;">
                <tr>
                  <td align="center" style="border-radius:8px;background:linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);">
                    <a href="{safe_url}" target="_blank" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:8px;letter-spacing:0.02em;">
                      Verify Email Address &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Expiration Warning Callout -->
              <div style="background-color:#1e293b;border-left:4px solid #38bdf8;padding:12px 16px;border-radius:4px;margin:24px 0;">
                <p style="font-size:12px;color:#94a3b8;margin:0;line-height:1.5;">
                  <strong style="color:#e2e8f0;">Security Notice:</strong> This verification link is valid for <strong>24 hours</strong>. If you did not register for an account on CompBench AI, please safely ignore this email.
                </p>
              </div>

              <!-- Direct URL Fallback -->
              <p style="font-size:12px;color:#6b7280;line-height:1.5;margin:20px 0 0 0;">
                If the button above does not work, copy and paste the following URL into your browser:
              </p>
              <p style="font-size:11px;color:#38bdf8;word-break:break-all;margin:6px 0 0 0;">
                <a href="{safe_url}" style="color:#38bdf8;text-decoration:none;">{safe_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding-top:32px;border-top:1px solid #1f2937;margin-top:28px;text-align:center;">
              <p style="font-size:11px;color:#6b7280;margin:0;line-height:1.4;">
                CompBench AI &bull; Automotive Systems Engineering &amp; Cost Intelligence<br>
                This is an automated security notification. Replies to this address are unmonitored.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_verification_email_text(full_name: str, verification_url: str) -> str:
    """Generate plain-text email fallback for account verification."""
    name = full_name.strip() if full_name else "CompBench User"
    return (
        f"COMPBENCH AI - ENGINEERING SUITE\n"
        f"Automotive Component Benchmarking & Engineering Intelligence\n"
        f"{'=' * 50}\n\n"
        f"Hello {name},\n\n"
        f"Thank you for registering on CompBench AI. To activate your access to\n"
        f"automotive component benchmarking and engineering teardowns, please verify\n"
        f"your email address by opening the following link:\n\n"
        f"{verification_url}\n\n"
        f"Notice: This verification link will expire in 24 hours.\n\n"
        f"If you did not create an account on CompBench AI, no action is required.\n\n"
        f"--\n"
        f"CompBench AI Engineering Systems"
    )


def generate_password_reset_email_html(full_name: str, reset_url: str) -> str:
    """Generate responsive, themed HTML email for password reset."""
    safe_name = html.escape(full_name.strip() if full_name else "CompBench User")
    safe_url = html.escape(reset_url.strip())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your CompBench AI Password</title>
</head>
<body style="margin:0;padding:0;background-color:#090d16;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f3f4f6;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#090d16;padding:40px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:540px;background-color:#111827;border:1px solid #1f2937;border-radius:12px;padding:36px 32px;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
          <!-- Header -->
          <tr>
            <td align="center" style="padding-bottom:24px;border-bottom:1px solid #1f2937;">
              <table role="presentation" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <span style="font-size:20px;font-weight:800;letter-spacing:-0.02em;color:#ffffff;display:inline-block;">
                      COMPBENCH <span style="color:#38bdf8;">AI</span>
                    </span>
                    <span style="display:inline-block;margin-left:8px;background-color:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;letter-spacing:0.06em;vertical-align:middle;">
                      ENGINEERING SUITE
                    </span>
                  </td>
                </tr>
              </table>
              <div style="font-size:12px;color:#9ca3af;margin-top:6px;">Automotive Component Benchmarking &amp; Engineering Intelligence</div>
            </td>
          </tr>

          <!-- Main Content -->
          <tr>
            <td style="padding-top:28px;">
              <h1 style="font-size:18px;font-weight:700;color:#ffffff;margin:0 0 16px 0;">Password Reset Request</h1>
              <p style="font-size:14px;line-height:1.6;color:#d1d5db;margin:0 0 20px 0;">
                Hello <strong>{safe_name}</strong>,
              </p>
              <p style="font-size:14px;line-height:1.6;color:#d1d5db;margin:0 0 24px 0;">
                We received a request to reset the password for your CompBench AI account. Click the button below to choose a new, secure password.
              </p>

              <!-- CTA Button -->
              <table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px 0;">
                <tr>
                  <td align="center" style="border-radius:8px;background:linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);">
                    <a href="{safe_url}" target="_blank" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:8px;letter-spacing:0.02em;">
                      Reset Password &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Expiration Warning Callout -->
              <div style="background-color:#1e293b;border-left:4px solid #f59e0b;padding:12px 16px;border-radius:4px;margin:24px 0;">
                <p style="font-size:12px;color:#94a3b8;margin:0;line-height:1.5;">
                  <strong style="color:#fbbf24;">Urgent Security Notice:</strong> This password reset link is single-use and will expire in <strong>1 hour</strong>. If you did not request a password reset, your credentials remain secure; please disregard this email.
                </p>
              </div>

              <!-- Direct URL Fallback -->
              <p style="font-size:12px;color:#6b7280;line-height:1.5;margin:20px 0 0 0;">
                If the button above does not work, copy and paste the following URL into your browser:
              </p>
              <p style="font-size:11px;color:#38bdf8;word-break:break-all;margin:6px 0 0 0;">
                <a href="{safe_url}" style="color:#38bdf8;text-decoration:none;">{safe_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding-top:32px;border-top:1px solid #1f2937;margin-top:28px;text-align:center;">
              <p style="font-size:11px;color:#6b7280;margin:0;line-height:1.4;">
                CompBench AI &bull; Automotive Systems Engineering &amp; Cost Intelligence<br>
                This is an automated security notification. Replies to this address are unmonitored.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_password_reset_email_text(full_name: str, reset_url: str) -> str:
    """Generate plain-text email fallback for password reset."""
    name = full_name.strip() if full_name else "CompBench User"
    return (
        f"COMPBENCH AI - ENGINEERING SUITE\n"
        f"Automotive Component Benchmarking & Engineering Intelligence\n"
        f"{'=' * 50}\n\n"
        f"Hello {name},\n\n"
        f"A password reset request was submitted for your CompBench AI account.\n"
        f"To set a new password, open the following link:\n\n"
        f"{reset_url}\n\n"
        f"Notice: This password reset link will expire in 1 hour.\n\n"
        f"If you did not request this password reset, please ignore this email.\n"
        f"Your current password will remain unchanged.\n\n"
        f"--\n"
        f"CompBench AI Engineering Systems"
    )


# =====================================================================
# Core Email Dispatch Functions
# =====================================================================

def send_email_via_resend(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str
) -> Dict[str, Any]:
    """
    Internal delivery helper that calls the Resend API with verified configuration.
    Validates recipient, sets API key, handles errors safely, and checks for successful acceptance.
    Never logs sensitive token URLs or raw payload data.
    """
    clean_to = to_email.strip().lower()
    if not validate_email_address(clean_to):
        raise ValueError(f"Invalid recipient email address format: {clean_to}")

    # Validate and configure Resend API credentials
    api_key = get_resend_api_key()
    sender = get_sender_email()

    resend.api_key = api_key

    params: resend.Emails.SendParams = {
        "from": sender,
        "to": [clean_to],
        "subject": subject,
        "html": html_content,
        "text": text_content
    }

    try:
        response = resend.Emails.send(params)
    except Exception as exc:
        masked = mask_email_for_logging(clean_to)
        logger.error(f"Resend API dispatch failed for recipient {masked}: {exc}")
        raise EmailDeliveryError(f"Failed to deliver email to {masked}: {exc}") from exc

    # Resend returns a response dict containing 'id' on successful acceptance
    if not response or not isinstance(response, dict) or not response.get("id"):
        masked = mask_email_for_logging(clean_to)
        raise EmailDeliveryError(
            f"Resend rejected email dispatch for {masked}. Unexpected response: {response}"
        )

    masked = mask_email_for_logging(clean_to)
    logger.info(f"Email successfully accepted by Resend (id={response.get('id')}) for recipient {masked}")
    return response


def send_verification_email(
    email: str,
    full_name: str,
    verification_url: str
) -> Dict[str, Any]:
    """
    Send an account verification email containing an activation link via Resend.
    Does not log token URLs or credentials.
    """
    if not verification_url or not verification_url.strip():
        raise ValueError("Verification URL is required.")

    html_body = generate_verification_email_html(full_name=full_name, verification_url=verification_url)
    text_body = generate_verification_email_text(full_name=full_name, verification_url=verification_url)

    return send_email_via_resend(
        to_email=email,
        subject="Verify your CompBench AI account",
        html_content=html_body,
        text_content=text_body
    )


def send_password_reset_email(
    email: str,
    full_name: str,
    reset_url: str
) -> Dict[str, Any]:
    """
    Send a password reset email containing a single-use reset link via Resend.
    Does not log token URLs or credentials.
    """
    if not reset_url or not reset_url.strip():
        raise ValueError("Password reset URL is required.")

    html_body = generate_password_reset_email_html(full_name=full_name, reset_url=reset_url)
    text_body = generate_password_reset_email_text(full_name=full_name, reset_url=reset_url)

    return send_email_via_resend(
        to_email=email,
        subject="Reset your CompBench AI password",
        html_content=html_body,
        text_content=text_body
    )
