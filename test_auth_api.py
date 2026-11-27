"""
CompBench AI - Phase 4: FastAPI Authentication & Multi-User API Test Suite.

Validates end-to-end HTTP API behavior for:
1. Public User Registration (POST /api/auth/register) & Validation.
2. Duplicate Registration Rejection (existing user and administrator email).
3. Email Verification (POST /api/auth/verify-email) with Token Lifecycle.
4. Resend Verification Token (POST /api/auth/resend-verification) with Anti-Enumeration.
5. User Login (POST /api/auth/login) Before & After Verification.
6. Environment Administrator Login Preservation (POST /api/auth/login).
7. Dual-Cookie Management (compbench_session HttpOnly + compbench_csrf JS-readable).
8. Logout & Complete Cookie Clearing (POST /api/auth/logout).
9. Authenticated Identity & Metadata (GET /api/auth/me).
10. Password Reset Flow (POST /api/auth/forgot-password & /api/auth/reset-password).
11. Genuine Session-Bound CSRF Validation (Cookie + Header + Session Claim Matching).
12. CORS Origin Whitelist Enforcement (No Wildcard Vercel Subdomains).
13. Role-Based Access Control (Admin vs Regular User on Protected Endpoints).
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure test environment
os.environ["TESTING"] = "1"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-for-phase4-api-tests-32-bytes"
os.environ["ADMIN_EMAIL"] = "admin@compbench.ai"
from argon2 import PasswordHasher
_ph = PasswordHasher(time_cost=2, memory_cost=4096, parallelism=1)
os.environ["ADMIN_PASSWORD_HASH"] = _ph.hash("AdminSecret2026!")

from fastapi.testclient import TestClient
from main import app, allowed_origins
from services.database import get_db_session, run_migrations, close_db_engine
from services.auth_service import (
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    create_session_token,
    get_csrf_token_from_session,
    verify_session_token
)
from models.user import User, EmailVerificationToken, PasswordResetToken

client = TestClient(app, base_url="http://localhost:8000")


def run_api_tests():
    print("=" * 60)
    print("COMPBENCH AI: PHASE 4 FASTAPI AUTHENTICATION API TEST SUITE")
    print("=" * 60)

    # Initialize SQLite in-memory database
    run_migrations()
    db = get_db_session()

    # -------------------------------------------------------------
    # 1. Public Registration: POST /api/auth/register
    # -------------------------------------------------------------
    print("\n--- 1. Public Registration (POST /api/auth/register) ---")
    with patch("services.auth_service.send_verification_email") as mock_email:
        # Successful registration
        reg_payload = {
            "full_name": "Alice Engineer",
            "email": "alice@automotive.com",
            "password": "SecurePassword2026!",
            "password_confirmation": "SecurePassword2026!"
        }
        res_reg = client.post("/api/auth/register", json=reg_payload)
        assert res_reg.status_code == 201, f"Expected 201, got {res_reg.status_code}: {res_reg.text}"
        data = res_reg.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "alice@automotive.com"
        assert data["user"]["role"] == "user"
        assert data["user"]["is_verified"] is False
        assert mock_email.called, "Verification email was not dispatched"
        print("  [OK] Public user registration succeeds with role='user' and is_verified=False")

        # Validation failure: Missing full name
        res_bad_name = client.post("/api/auth/register", json={
            "full_name": "",
            "email": "bad@test.com",
            "password": "Password123!"
        })
        assert res_bad_name.status_code == 400
        assert "name is required" in res_bad_name.json()["detail"].lower()

        # Validation failure: Short password (<8 chars)
        res_short_pass = client.post("/api/auth/register", json={
            "full_name": "Bob Tester",
            "email": "bob@test.com",
            "password": "short"
        })
        assert res_short_pass.status_code == 400
        assert "at least 8 characters" in res_short_pass.json()["detail"].lower()

        # Validation failure: Mismatched password confirmation
        res_mismatch = client.post("/api/auth/register", json={
            "full_name": "Bob Tester",
            "email": "bob@test.com",
            "password": "Password123!",
            "password_confirmation": "DifferentPassword123!"
        })
        assert res_mismatch.status_code == 400
        assert "do not match" in res_mismatch.json()["detail"].lower()
        print("  [OK] Registration validation rejected missing fields, short passwords, and confirmation mismatch")

    # -------------------------------------------------------------
    # 2. Duplicate Registration Rejection
    # -------------------------------------------------------------
    print("\n--- 2. Duplicate Email Registration Rejection ---")
    with patch("services.auth_service.send_verification_email"):
        # Duplicate user email
        res_dup_user = client.post("/api/auth/register", json=reg_payload)
        assert res_dup_user.status_code == 409
        assert "already exists" in res_dup_user.json()["detail"].lower()
        print("  [OK] Duplicate registration rejected with HTTP 409 Conflict for existing user")

        # Registration using configured administrator email
        res_dup_admin = client.post("/api/auth/register", json={
            "full_name": "Attacker Admin",
            "email": "admin@compbench.ai",
            "password": "MaliciousPassword2026!"
        })
        assert res_dup_admin.status_code == 409
        assert "already exists" in res_dup_admin.json()["detail"].lower()
        print("  [OK] Registration rejected with HTTP 409 Conflict when attempting to register administrator email")

    # -------------------------------------------------------------
    # 3. Email Verification: POST /api/auth/verify-email
    # -------------------------------------------------------------
    print("\n--- 3. Email Verification Flow (POST /api/auth/verify-email) ---")
    # Retrieve raw token generated during registration
    user_db = db.query(User).filter_by(email="alice@automotive.com").first()
    assert user_db is not None
    token_record = db.query(EmailVerificationToken).filter_by(user_id=user_db.id).first()
    assert token_record is not None

    # We extract raw token from mock call
    raw_verification_token = mock_email.call_args[1]["verification_url"].split("token=")[1]

    # Verification attempt with invalid token
    res_bad_token = client.post("/api/auth/verify-email", json={"token": "invalid-token-value"})
    assert res_bad_token.status_code == 400
    assert "invalid" in res_bad_token.json()["detail"].lower()

    # Valid verification
    res_verify = client.post("/api/auth/verify-email", json={"token": raw_verification_token})
    assert res_verify.status_code == 200
    assert res_verify.json()["user"]["is_verified"] is True
    print("  [OK] Valid email verification token sets is_verified=True")

    # Reused token attempt
    res_reused = client.post("/api/auth/verify-email", json={"token": raw_verification_token})
    assert res_reused.status_code == 400
    assert "already been used" in res_reused.json()["detail"].lower()
    print("  [OK] Reused email verification token rejected with HTTP 400 Bad Request")

    # -------------------------------------------------------------
    # 4. Resend Verification: POST /api/auth/resend-verification
    # -------------------------------------------------------------
    print("\n--- 4. Resend Verification Email (POST /api/auth/resend-verification) ---")
    with patch("services.auth_service.send_verification_email") as mock_resend:
        # Register second unverified user
        client.post("/api/auth/register", json={
            "full_name": "Charlie Unverified",
            "email": "charlie@automotive.com",
            "password": "Password2026!"
        })

        # Resend to unverified account
        res_resend = client.post("/api/auth/resend-verification", json={"email": "charlie@automotive.com"})
        assert res_resend.status_code == 200
        assert mock_resend.called

        # Resend to unknown account (anti-enumeration: must return identical message)
        mock_resend.reset_mock()
        res_unknown = client.post("/api/auth/resend-verification", json={"email": "nonexistent@automotive.com"})
        assert res_unknown.status_code == 200
        assert res_unknown.json()["message"] == res_resend.json()["message"]
        assert not mock_resend.called, "Should not dispatch email for nonexistent address"
        print("  [OK] Resend verification provides generic response preventing email enumeration")

    # -------------------------------------------------------------
    # 5. User Login: POST /api/auth/login
    # -------------------------------------------------------------
    print("\n--- 5. User Authentication & Login Verification ---")
    # Unverified user login attempt
    res_unverified_login = client.post("/api/auth/login", json={
        "email": "charlie@automotive.com",
        "password": "Password2026!"
    })
    assert res_unverified_login.status_code == 403
    assert "not verified" in res_unverified_login.json()["detail"].lower()
    print("  [OK] Unverified user login strictly blocked with HTTP 403 Forbidden")

    # Verified user login with wrong password
    res_bad_pass = client.post("/api/auth/login", json={
        "email": "alice@automotive.com",
        "password": "WrongPassword!"
    })
    assert res_bad_pass.status_code == 401
    assert "invalid" in res_bad_pass.json()["detail"].lower()

    # Verified user login with correct password
    res_login_user = client.post("/api/auth/login", json={
        "email": "alice@automotive.com",
        "password": "SecurePassword2026!"
    })
    assert res_login_user.status_code == 200
    user_data = res_login_user.json()
    assert user_data["user"]["email"] == "alice@automotive.com"
    assert user_data["user"]["role"] == "user"
    assert "token" not in user_data, "Browser login response must NOT expose raw session token in JSON"
    assert "csrf_token" in user_data

    # Verify cookies
    assert SESSION_COOKIE_NAME in res_login_user.cookies
    assert CSRF_COOKIE_NAME in res_login_user.cookies
    user_session_token = res_login_user.cookies[SESSION_COOKIE_NAME]
    user_csrf_token = res_login_user.cookies[CSRF_COOKIE_NAME]
    assert user_csrf_token == user_data["csrf_token"]
    print("  [OK] Verified user login succeeds, sets dual cookies (compbench_session & compbench_csrf)")

    # -------------------------------------------------------------
    # 6. Administrator Login Preservation
    # -------------------------------------------------------------
    print("\n--- 6. Environment Administrator Login Preservation ---")
    res_admin_login = client.post("/api/auth/login", json={
        "email": "admin@compbench.ai",
        "password": "AdminSecret2026!"
    })
    assert res_admin_login.status_code == 200
    admin_data = res_admin_login.json()
    assert admin_data["user"]["email"] == "admin@compbench.ai"
    assert admin_data["user"]["role"] == "admin"
    assert "token" not in admin_data, "Administrator login response must NOT expose raw session token in JSON"
    admin_session_token = res_admin_login.cookies[SESSION_COOKIE_NAME]
    admin_csrf_token = res_admin_login.cookies[CSRF_COOKIE_NAME]
    assert admin_csrf_token == admin_data["csrf_token"]
    print("  [OK] Environment-configured administrator login preserved with role='admin'")

    # -------------------------------------------------------------
    # 7. Identity & Metadata: GET /api/auth/me
    # -------------------------------------------------------------
    print("\n--- 7. Identity Route (GET /api/auth/me) ---")
    client.cookies.clear()
    # Unauthenticated
    res_me_unauth = client.get("/api/auth/me")
    assert res_me_unauth.status_code == 401

    # Authenticated User
    client.cookies.clear()
    res_me_user = client.get("/api/auth/me", cookies={SESSION_COOKIE_NAME: user_session_token})
    assert res_me_user.status_code == 200
    me_user_data = res_me_user.json()
    assert me_user_data["authenticated"] is True
    assert me_user_data["user"]["email"] == "alice@automotive.com"
    assert me_user_data["user"]["name"] == "Alice Engineer"
    assert me_user_data["user"]["role"] == "user"
    assert me_user_data["csrf_token"] == user_csrf_token
    print("  [OK] GET /api/auth/me returns actual user name, email, role='user', and csrf_token")

    # Authenticated Administrator
    client.cookies.clear()
    res_me_admin = client.get("/api/auth/me", cookies={SESSION_COOKIE_NAME: admin_session_token})
    assert res_me_admin.status_code == 200
    me_admin_data = res_me_admin.json()
    assert me_admin_data["user"]["email"] == "admin@compbench.ai"
    assert me_admin_data["user"]["role"] == "admin"
    print("  [OK] GET /api/auth/me returns administrator identity and role='admin'")

    # -------------------------------------------------------------
    # 8. Password Reset Flow: Forgot & Reset Password
    # -------------------------------------------------------------
    print("\n--- 8. Password Reset Flow (Forgot & Reset Password) ---")
    client.cookies.clear()
    with patch("services.auth_service.send_password_reset_email") as mock_reset_email:
        # Request password reset for verified user
        res_forgot = client.post("/api/auth/forgot-password", json={"email": "alice@automotive.com"})
        assert res_forgot.status_code == 200
        assert mock_reset_email.called
        raw_reset_token = mock_reset_email.call_args[1]["reset_url"].split("token=")[1]

        # Request password reset for unknown user (anti-enumeration)
        mock_reset_email.reset_mock()
        res_forgot_unknown = client.post("/api/auth/forgot-password", json={"email": "ghost@automotive.com"})
        assert res_forgot_unknown.status_code == 200
        assert res_forgot_unknown.json()["message"] == res_forgot.json()["message"]
        assert not mock_reset_email.called
        print("  [OK] Forgot-password provides generic response preventing account enumeration")

        # Execute reset with invalid token
        res_reset_bad = client.post("/api/auth/reset-password", json={
            "token": "invalid-reset-token",
            "new_password": "BrandNewPassword2026!"
        })
        assert res_reset_bad.status_code == 400

        # Execute reset with short password
        res_reset_short = client.post("/api/auth/reset-password", json={
            "token": raw_reset_token,
            "new_password": "short"
        })
        assert res_reset_short.status_code == 400

        # Execute successful password reset
        res_reset_ok = client.post("/api/auth/reset-password", json={
            "token": raw_reset_token,
            "new_password": "BrandNewPassword2026!",
            "password_confirmation": "BrandNewPassword2026!"
        })
        assert res_reset_ok.status_code == 200
        print("  [OK] Password successfully reset")

        # Verify old session token is invalidated
        assert verify_session_token(user_session_token) is None, "Old session was not invalidated upon password reset"

        # Old password login must fail
        res_old_login = client.post("/api/auth/login", json={
            "email": "alice@automotive.com",
            "password": "SecurePassword2026!"
        })
        assert res_old_login.status_code == 401

        # New password login succeeds
        res_new_login = client.post("/api/auth/login", json={
            "email": "alice@automotive.com",
            "password": "BrandNewPassword2026!"
        })
        assert res_new_login.status_code == 200
        assert "token" not in res_new_login.json(), "Password-reset login response must NOT expose raw session token in JSON"
        user_session_token = res_new_login.cookies[SESSION_COOKIE_NAME]
        user_csrf_token = res_new_login.cookies[CSRF_COOKIE_NAME]
        print("  [OK] Previous sessions invalidated; old password rejected, new password authenticated")

    # -------------------------------------------------------------
    # 9. Session-Bound CSRF Validation on State-Changing API Calls
    # -------------------------------------------------------------
    print("\n--- 9. Genuine Session-Bound CSRF Validation ---")
    client.cookies.clear()
    csrf_headers_ok = {
        "Origin": "http://localhost:8000",
        "Host": "localhost:8000",
        "X-CompBench-CSRF": user_csrf_token
    }
    csrf_cookies_ok = {
        SESSION_COOKIE_NAME: user_session_token,
        CSRF_COOKIE_NAME: user_csrf_token
    }

    # A. Valid request with matching header, cookie, and session claim -> 200 OK
    client.cookies.clear()
    res_compare_ok = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers=csrf_headers_ok,
        cookies=csrf_cookies_ok
    )
    assert res_compare_ok.status_code == 200
    print("  [OK] Valid cookie-authenticated request with matching CSRF cookie, header & session claim succeeds")

    # B. Missing X-CompBench-CSRF header -> 403 Forbidden
    client.cookies.clear()
    res_missing_header = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers={"Origin": "http://localhost:8000", "Host": "localhost:8000"},
        cookies=csrf_cookies_ok
    )
    assert res_missing_header.status_code == 403
    assert "missing x-compbench-csrf header" in res_missing_header.json()["detail"].lower()
    print("  [OK] Missing X-CompBench-CSRF header rejected with HTTP 403")

    # C. Missing compbench_csrf cookie -> 403 Forbidden
    client.cookies.clear()
    res_missing_cookie = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers=csrf_headers_ok,
        cookies={SESSION_COOKIE_NAME: user_session_token}
    )
    assert res_missing_cookie.status_code == 403
    assert "missing compbench_csrf cookie" in res_missing_cookie.json()["detail"].lower()
    print("  [OK] Missing compbench_csrf cookie rejected with HTTP 403")

    # D. Static CSRF token ('1') rejected -> 403 Forbidden
    client.cookies.clear()
    res_static_csrf = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers={"Origin": "http://localhost:8000", "Host": "localhost:8000", "X-CompBench-CSRF": "1"},
        cookies={SESSION_COOKIE_NAME: user_session_token, CSRF_COOKIE_NAME: "1"}
    )
    assert res_static_csrf.status_code == 403
    assert "static csrf tokens" in res_static_csrf.json()["detail"].lower()
    print("  [OK] Static CSRF token ('1') strictly rejected with HTTP 403")

    # E. Mismatched header vs cookie -> 403 Forbidden
    client.cookies.clear()
    res_mismatched = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers=csrf_headers_ok,
        cookies={SESSION_COOKIE_NAME: user_session_token, CSRF_COOKIE_NAME: "different_csrf_cookie_value"}
    )
    assert res_mismatched.status_code == 403
    assert "do not match" in res_mismatched.json()["detail"].lower()
    print("  [OK] Mismatched header and cookie rejected with HTTP 403")

    # F. Forged CSRF matching cookie but not matching session claim -> 403 Forbidden
    client.cookies.clear()
    forged_token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    res_forged = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers={"Origin": "http://localhost:8000", "Host": "localhost:8000", "X-CompBench-CSRF": forged_token},
        cookies={SESSION_COOKIE_NAME: user_session_token, CSRF_COOKIE_NAME: forged_token}
    )
    assert res_forged.status_code == 403
    assert "does not match authenticated session" in res_forged.json()["detail"].lower()
    print("  [OK] Forged CSRF token not matching session claim rejected with HTTP 403")

    # G. Untrusted Origin -> 403 Forbidden
    client.cookies.clear()
    res_untrusted_origin = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers={"Origin": "https://malicious-attacker.com", "Host": "localhost:8000", "X-CompBench-CSRF": user_csrf_token},
        cookies=csrf_cookies_ok
    )
    assert res_untrusted_origin.status_code == 403
    assert "untrusted origin" in res_untrusted_origin.json()["detail"].lower()
    print("  [OK] Untrusted origin rejected with HTTP 403 even with matching CSRF tokens")

    # H. Bearer-only authentication exempt from browser CSRF -> 200 OK
    client.cookies.clear()
    res_bearer = client.post(
        "/compare",
        json={"component_a_id": "CB001", "component_b_id": "CB002"},
        headers={"Authorization": f"Bearer {user_session_token}"}
    )
    assert res_bearer.status_code == 200
    print("  [OK] Bearer-token authentication without session cookie exempt from browser CSRF")

    # -------------------------------------------------------------
    # 10. CORS Whitelist Security (No Wildcard Vercel Subdomain)
    # -------------------------------------------------------------
    print("\n--- 10. CORS Whitelist Enforcement ---")
    assert "http://localhost:8000" in allowed_origins
    assert "http://127.0.0.1:8000" in allowed_origins
    # Wildcard regex must NOT be in CORS origins
    assert not any("*" in o for o in allowed_origins)
    print("  [OK] CORS restricted strictly to explicitly allowed origins without wildcard subdomains")

    # -------------------------------------------------------------
    # 11. Role-Based Access Control (Admin vs Regular User)
    # -------------------------------------------------------------
    print("\n--- 11. Role-Based Access Control Enforcement ---")
    # Regular user attempting admin endpoint -> 403 Forbidden
    client.cookies.clear()
    res_user_admin_ep = client.get(
        "/api/admin/system-status",
        cookies={SESSION_COOKIE_NAME: user_session_token}
    )
    assert res_user_admin_ep.status_code == 403
    assert "administrator privileges required" in res_user_admin_ep.json()["detail"].lower()
    print("  [OK] Regular user blocked with HTTP 403 Forbidden on administrator endpoint")

    # Administrator accessing admin endpoint -> 200 OK
    client.cookies.clear()
    res_admin_admin_ep = client.get(
        "/api/admin/system-status",
        cookies={SESSION_COOKIE_NAME: admin_session_token}
    )
    assert res_admin_admin_ep.status_code == 200
    assert res_admin_admin_ep.json()["status"] == "operational"
    print("  [OK] Administrator successfully accesses administrative endpoint")

    # -------------------------------------------------------------
    # 12. Logout & Complete Cookie Clearing: POST /api/auth/logout
    # -------------------------------------------------------------
    print("\n--- 12. Logout & Cookie Disposal (POST /api/auth/logout) ---")
    client.cookies.clear()
    res_logout = client.post(
        "/api/auth/logout",
        cookies={SESSION_COOKIE_NAME: user_session_token, CSRF_COOKIE_NAME: user_csrf_token}
    )
    assert res_logout.status_code == 200
    # Both cookies must be deleted
    assert SESSION_COOKIE_NAME not in res_logout.cookies
    assert CSRF_COOKIE_NAME not in res_logout.cookies
    # Token must be revoked on server side
    assert verify_session_token(user_session_token) is None
    print("  [OK] Logout clears both cookies and revokes session token server-side")

    # Clean up DB
    db.close()
    close_db_engine()

    print("\n============================================================")
    print("ALL PHASE 4 FASTAPI AUTHENTICATION API TESTS PASSED!")
    print("============================================================")


if __name__ == "__main__":
    run_api_tests()

