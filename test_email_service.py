"""
Unit Test Suite for CompBench AI Email Delivery Service (Phase 2).

Validates:
1. Resend API key and sender configuration validation (no hardcoded keys).
2. Email address format validation (RFC 5322 compliance).
3. Responsive, themed HTML and plain-text template generation.
4. XSS protection: HTML escaping of user input in templates.
5. Verification email link structure and 24-hour expiration notice.
6. Password reset email link structure and 1-hour expiration notice.
7. Mocked Resend API delivery (no actual emails sent during testing).
8. API error handling, rejected response handling, and secure email masking for logs.
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["TESTING"] = "1"

from services.email_service import (
    get_resend_api_key,
    get_sender_email,
    get_app_base_url,
    validate_email_address,
    mask_email_for_logging,
    generate_verification_email_html,
    generate_verification_email_text,
    generate_password_reset_email_html,
    generate_password_reset_email_text,
    send_verification_email,
    send_password_reset_email,
    EmailConfigurationError,
    EmailDeliveryError
)


def run_email_service_test_suite():
    print("============================================================")
    print("COMPBENCH AI: RESEND EMAIL SERVICE TEST SUITE (PHASE 2)")
    print("============================================================")

    # -------------------------------------------------------------
    # 1. Configuration Validation & Fail-Secure Behavior
    # -------------------------------------------------------------
    print("\n--- 1. Configuration Validation & Fail-Secure Checks ---")
    saved_key = os.environ.get("RESEND_API_KEY")
    saved_sender = os.environ.get("RESEND_FROM_EMAIL")
    saved_app_url = os.environ.get("APP_BASE_URL")

    try:
        # Missing API key must raise EmailConfigurationError
        os.environ.pop("RESEND_API_KEY", None)
        try:
            get_resend_api_key()
            assert False, "Expected EmailConfigurationError on missing RESEND_API_KEY"
        except EmailConfigurationError as e:
            assert "RESEND_API_KEY environment variable is not configured" in str(e)
            print("  [OK] Missing RESEND_API_KEY safely raises EmailConfigurationError")

        # Invalid API key prefix must raise EmailConfigurationError
        os.environ["RESEND_API_KEY"] = "invalid_prefix_key_12345"
        try:
            get_resend_api_key()
            assert False, "Expected EmailConfigurationError on key without 're_' prefix"
        except EmailConfigurationError as e:
            assert "must start with 're_'" in str(e)
            print("  [OK] Invalid RESEND_API_KEY format safely rejected")

        # Valid API key prefix
        os.environ["RESEND_API_KEY"] = "re_test_mock_secret_key_abcdef123456"
        assert get_resend_api_key() == "re_test_mock_secret_key_abcdef123456"
        print("  [OK] Valid RESEND_API_KEY accepted correctly")

        # Sender email defaults and overrides
        os.environ.pop("RESEND_FROM_EMAIL", None)
        assert get_sender_email() == "CompBench AI <onboarding@resend.dev>"
        os.environ["RESEND_FROM_EMAIL"] = "CompBench <noreply@compbench.ai>"
        assert get_sender_email() == "CompBench <noreply@compbench.ai>"
        print("  [OK] Sender email defaults safely and accepts custom domain override")

        # Base URL defaults and overrides
        os.environ.pop("APP_BASE_URL", None)
        assert get_app_base_url() == "http://localhost:8000"
        os.environ["APP_BASE_URL"] = "https://compbench.ai/"
        assert get_app_base_url() == "https://compbench.ai"  # trailing slash stripped
        print("  [OK] Application base URL defaults safely and normalizes trailing slashes")

    finally:
        if saved_key is not None:
            os.environ["RESEND_API_KEY"] = saved_key
        else:
            os.environ.pop("RESEND_API_KEY", None)

        if saved_sender is not None:
            os.environ["RESEND_FROM_EMAIL"] = saved_sender
        else:
            os.environ.pop("RESEND_FROM_EMAIL", None)

        if saved_app_url is not None:
            os.environ["APP_BASE_URL"] = saved_app_url
        else:
            os.environ.pop("APP_BASE_URL", None)

    # -------------------------------------------------------------
    # 2. Email Address Validation & Privacy Masking
    # -------------------------------------------------------------
    print("\n--- 2. Email Format Validation & Privacy Masking ---")
    assert validate_email_address("engineer@compbench.ai") is True
    assert validate_email_address("first.last+tag@sub.domain.com") is True
    assert validate_email_address("invalid-email-address") is False
    assert validate_email_address("@missing-local.com") is False
    assert validate_email_address("missing-domain@") is False
    assert validate_email_address("") is False
    print("  [OK] Email address format validation correctly identifies valid and invalid addresses")

    # Verify privacy masking for safe application logs
    assert mask_email_for_logging("engineer@compbench.ai") == "en***r@compbench.ai"
    assert mask_email_for_logging("ab@example.com") == "a*@example.com"
    assert mask_email_for_logging("invalid") == "[masked-email]"
    print("  [OK] Email privacy masking successfully masks recipient identities in logs")

    # -------------------------------------------------------------
    # 3. Account Verification Email Template Generation
    # -------------------------------------------------------------
    print("\n--- 3. Account Verification Template Verification ---")
    test_name = "Alex Mercer <script>alert(1)</script>"
    test_verify_url = "http://localhost:8000/verify-email?token=sec_token_12345"

    html_out = generate_verification_email_html(test_name, test_verify_url)
    text_out = generate_verification_email_text(test_name, test_verify_url)

    # HTML checks
    assert "Alex Mercer &lt;script&gt;alert(1)&lt;/script&gt;" in html_out, "XSS vulnerability: name unescaped in HTML"
    assert "<script>alert" not in html_out, "Raw script tag present in HTML!"
    assert test_verify_url in html_out, "Verification URL missing from HTML"
    assert "24 hours" in html_out, "24-hour expiration notice missing from HTML"
    assert "COMPBENCH" in html_out and "ENGINEERING SUITE" in html_out
    assert "Verify Email Address" in html_out
    print("  [OK] Verification HTML template generated: XSS safe, themed, contains 24h expiration")

    # Plain text checks
    assert test_verify_url in text_out
    assert "24 hours" in text_out
    assert "Alex Mercer" in text_out
    print("  [OK] Verification plain-text template generated with full fallback content")

    # -------------------------------------------------------------
    # 4. Password Reset Email Template Generation
    # -------------------------------------------------------------
    print("\n--- 4. Password Reset Template Verification ---")
    test_reset_url = "http://localhost:8000/reset-password?token=sec_reset_token_67890"

    reset_html = generate_password_reset_email_html("Sarah Connor", test_reset_url)
    reset_text = generate_password_reset_email_text("Sarah Connor", test_reset_url)

    # HTML checks
    assert "Sarah Connor" in reset_html
    assert test_reset_url in reset_html
    assert "1 hour" in reset_html, "1-hour expiration notice missing from reset HTML"
    assert "Reset Password" in reset_html
    print("  [OK] Password reset HTML template generated: themed, contains 1h expiration notice")

    # Plain text checks
    assert test_reset_url in reset_text
    assert "1 hour" in reset_text
    assert "Sarah Connor" in reset_text
    print("  [OK] Password reset plain-text template generated with full fallback content")

    # -------------------------------------------------------------
    # 5. Mocked Resend Delivery: Verification Email
    # -------------------------------------------------------------
    print("\n--- 5. Mocked Resend Verification Email Delivery ---")
    os.environ["RESEND_API_KEY"] = "re_mock_test_key_999"
    os.environ["RESEND_FROM_EMAIL"] = "CompBench AI <onboarding@resend.dev>"

    with patch("resend.Emails.send") as mock_resend_send:
        mock_resend_send.return_value = {
            "id": "email_msg_uuid_123456789",
            "from": "CompBench AI <onboarding@resend.dev>",
            "to": ["user@automotive.org"],
            "created_at": "2026-11-26T12:00:00Z"
        }

        response = send_verification_email(
            email="user@automotive.org",
            full_name="Vehicle Architect",
            verification_url=test_verify_url
        )

        assert response["id"] == "email_msg_uuid_123456789"
        assert mock_resend_send.called
        call_args = mock_resend_send.call_args[0][0]
        assert call_args["from"] == "CompBench AI <onboarding@resend.dev>"
        assert call_args["to"] == ["user@automotive.org"]
        assert call_args["subject"] == "Verify your CompBench AI account"
        assert "Verify Email Address" in call_args["html"]
        assert test_verify_url in call_args["text"]
        print("  [OK] send_verification_email called Resend SDK with verified parameters and returned delivery ID")

    # -------------------------------------------------------------
    # 6. Mocked Resend Delivery: Password Reset Email
    # -------------------------------------------------------------
    print("\n--- 6. Mocked Resend Password Reset Email Delivery ---")
    with patch("resend.Emails.send") as mock_resend_send:
        mock_resend_send.return_value = {
            "id": "reset_msg_uuid_987654321",
            "from": "CompBench AI <onboarding@resend.dev>",
            "to": ["lead@automotive.org"],
            "created_at": "2026-11-26T12:00:00Z"
        }

        response = send_password_reset_email(
            email="lead@automotive.org",
            full_name="Lead Cost Engineer",
            reset_url=test_reset_url
        )

        assert response["id"] == "reset_msg_uuid_987654321"
        assert mock_resend_send.called
        call_args = mock_resend_send.call_args[0][0]
        assert call_args["subject"] == "Reset your CompBench AI password"
        assert "Reset Password" in call_args["html"]
        print("  [OK] send_password_reset_email called Resend SDK with verified parameters and returned delivery ID")

    # -------------------------------------------------------------
    # 7. Error Handling & Delivery Rejections
    # -------------------------------------------------------------
    print("\n--- 7. Error Handling & Resend Delivery Failures ---")

    # A. Invalid recipient email
    try:
        send_verification_email("invalid-email", "User", test_verify_url)
        assert False, "Expected ValueError on invalid email format"
    except ValueError as e:
        assert "Invalid recipient email" in str(e)
        print("  [OK] Malformed recipient email rejected with ValueError")

    # B. Missing verification URL
    try:
        send_verification_email("valid@email.com", "User", "")
        assert False, "Expected ValueError on empty URL"
    except ValueError as e:
        assert "Verification URL is required" in str(e)
        print("  [OK] Empty verification URL rejected with ValueError")

    # C. Resend API Network/Server Exception
    with patch("resend.Emails.send") as mock_resend_error:
        mock_resend_error.side_effect = Exception("Connection timed out to api.resend.com")

        try:
            send_verification_email("user@test.com", "User", test_verify_url)
            assert False, "Expected EmailDeliveryError when Resend raises an exception"
        except EmailDeliveryError as e:
            assert "Failed to deliver email" in str(e)
            print("  [OK] Resend API exception caught and re-raised as EmailDeliveryError")

    # D. Resend Rejection (Response missing 'id')
    with patch("resend.Emails.send") as mock_resend_reject:
        mock_resend_reject.return_value = {"error": "Domain not verified"}

        try:
            send_password_reset_email("user@test.com", "User", test_reset_url)
            assert False, "Expected EmailDeliveryError when Resend response lacks 'id'"
        except EmailDeliveryError as e:
            assert "Resend rejected email dispatch" in str(e)
            print("  [OK] Response lacking 'id' safely caught and flagged as EmailDeliveryError")

    # Clean up test env
    os.environ.pop("RESEND_API_KEY", None)
    os.environ.pop("RESEND_FROM_EMAIL", None)

    print("\n============================================================")
    print("ALL PHASE 2 EMAIL SERVICE TESTS PASSED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    run_email_service_test_suite()
