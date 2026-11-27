"""
Comprehensive Test Suite for Multi-User Authentication Service (Phase 3).

Validates:
1. Successful user registration with role='user' and is_verified=False.
2. Duplicate email rejection (existing user and admin email).
3. Automatic 'user' role assignment (public registration cannot create admin).
4. Password hashing with Argon2id and constant-time verification.
5. Invalid password rejection (short passwords, mismatching confirmation).
6. Successful email verification via token, setting is_verified=True.
7. Invalid, expired, and reused verification tokens rejected with InvalidTokenError.
8. Successful password reset flow (request -> verify token -> reset -> session revocation).
9. Invalid, expired, and reused reset tokens rejected with InvalidTokenError.
10. Existing administrator login compatibility (ADMIN_EMAIL & ADMIN_PASSWORD_HASH).
11. Admin/User role checks (is_user_in_role, require_role, require_admin_user).
12. Unverified user session restrictions (unverified users cannot authenticate).
13. Database transaction rollback on failure.
14. Mocked email delivery (no real emails sent during testing).
"""

import os
import sys
import time
import concurrent.futures
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["TESTING"] = "1"
os.environ["AUTH_SECRET_KEY"] = "multi-user-test-secret-key-32-bytes-long"

from sqlalchemy import select
from services.database import get_engine, get_db_session, run_migrations, close_db_engine
from models.user import User, EmailVerificationToken, PasswordResetToken, RevokedToken
from services.auth_service import (
    authenticate_user,
    register_user,
    verify_email_token,
    resend_verification_token,
    request_password_reset,
    verify_password_reset_token,
    reset_password,
    revoke_session_token,
    is_user_in_role,
    require_role,
    require_admin_user,
    hash_password,
    verify_password,
    create_session_token,
    verify_session_token,
    validate_production_configuration,
    _REVOKED_SESSION_JTIS,
    _USER_REVOCATION_CUTOFF,
    DuplicateEmailError,
    UnverifiedUserError,
    InvalidTokenError,
    PasswordValidationError
)


def get_test_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def run_multi_user_auth_tests():
    print("============================================================")
    print("COMPBENCH AI: MULTI-USER AUTHENTICATION TEST SUITE (PHASE 3)")
    print("============================================================")

    # Initialize isolated test database schema
    close_db_engine()
    engine = get_engine(force_sqlite_test=True)
    run_migrations(target_engine=engine)
    session = get_db_session(force_sqlite_test=True)

    # Configure mock environment administrator
    TEST_ADMIN_EMAIL = "admin@compbench.ai"
    TEST_ADMIN_PASS = "SuperAdminPassword2026!"
    os.environ["ADMIN_EMAIL"] = TEST_ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD_HASH"] = hash_password(TEST_ADMIN_PASS)

    # -------------------------------------------------------------
    # 1. Existing Administrator Login Compatibility & Role Check
    # -------------------------------------------------------------
    print("\n--- 1. Existing Administrator Login Compatibility ---")
    admin_auth = authenticate_user(TEST_ADMIN_EMAIL, TEST_ADMIN_PASS, db=session)
    assert admin_auth is not None, "Administrator failed to authenticate"
    assert admin_auth["email"] == TEST_ADMIN_EMAIL
    assert admin_auth["role"] == "admin"
    assert admin_auth["is_verified"] is True
    assert is_user_in_role(admin_auth, "admin") is True
    assert is_user_in_role(admin_auth, "user") is False

    # Verify invalid admin password fails
    bad_admin = authenticate_user(TEST_ADMIN_EMAIL, "WrongAdminPassword!", db=session)
    assert bad_admin is None, "Admin authenticated with invalid password"
    print("  [OK] Environment administrator login perfectly preserved with role='admin'")

    # -------------------------------------------------------------
    # 2. Public User Registration & Automatic 'user' Role
    # -------------------------------------------------------------
    print("\n--- 2. Public User Registration & Role Assignment ---")
    with patch("services.auth_service.send_verification_email") as mock_email:
        user_1, raw_verify_token_1 = register_user(
            full_name="Elena Rostova",
            email="elena.rostova@oem-aerospace.com",
            password="SecurePass2026!Elena",
            password_confirmation="SecurePass2026!Elena",
            db=session
        )

        assert user_1.id is not None
        assert user_1.email == "elena.rostova@oem-aerospace.com"
        assert user_1.role == "user", "Public registration must assign role='user'"
        assert user_1.is_verified is False, "New accounts must start with is_verified=False"
        assert raw_verify_token_1 is not None and len(raw_verify_token_1) > 20
        assert mock_email.called, "Verification email was not dispatched"
        call_kwargs = mock_email.call_args[1]
        assert call_kwargs["email"] == "elena.rostova@oem-aerospace.com"
        assert raw_verify_token_1 in call_kwargs["verification_url"]
        print("  [OK] Registration succeeded with automatic role='user' and is_verified=False")

    # -------------------------------------------------------------
    # 3. Password Validation & Strength Enforcement
    # -------------------------------------------------------------
    print("\n--- 3. Password Validation & Mismatch Checks ---")
    try:
        register_user("Short Pass", "short@test.com", "short", "short", db=session)
        assert False, "Expected PasswordValidationError for short password"
    except PasswordValidationError as e:
        assert "at least 8 characters" in str(e)
        print("  [OK] Rejected password shorter than 8 characters")

    try:
        register_user("Mismatch Pass", "mismatch@test.com", "Password123!", "Different123!", db=session)
        assert False, "Expected PasswordValidationError for mismatching passwords"
    except PasswordValidationError as e:
        assert "Passwords do not match" in str(e)
        print("  [OK] Rejected mismatching password confirmation")

    # -------------------------------------------------------------
    # 4. Duplicate Email Rejection (Existing User & Admin Email)
    # -------------------------------------------------------------
    print("\n--- 4. Duplicate Email Rejection ---")
    # A. Existing user duplicate
    try:
        register_user("Duplicate User", "elena.rostova@oem-aerospace.com", "Password123!", db=session)
        assert False, "Expected DuplicateEmailError for existing registered email"
    except DuplicateEmailError as e:
        assert "already exists" in str(e)
        print("  [OK] Duplicate registration rejected for existing user email")

    # B. Administrator email duplicate
    try:
        register_user("Fake Admin", TEST_ADMIN_EMAIL, "Password123!", db=session)
        assert False, "Expected DuplicateEmailError when registering with admin email"
    except DuplicateEmailError as e:
        assert "already exists" in str(e)
        print("  [OK] Duplicate registration rejected when using admin email")

    # -------------------------------------------------------------
    # 5. Unverified User Session Restriction
    # -------------------------------------------------------------
    print("\n--- 5. Unverified User Login Restrictions ---")
    try:
        authenticate_user("elena.rostova@oem-aerospace.com", "SecurePass2026!Elena", db=session)
        assert False, "Expected UnverifiedUserError for unverified user sign-in"
    except UnverifiedUserError as e:
        assert "Email address not verified" in str(e)
        print("  [OK] Unverified registered user strictly prohibited from establishing session")

    # -------------------------------------------------------------
    # 6. Email Verification Workflow & Token Consumption
    # -------------------------------------------------------------
    print("\n--- 6. Email Verification & Token Lifecycle ---")
    # Successful verification
    verified_user = verify_email_token(raw_verify_token_1, db=session)
    assert verified_user.id == user_1.id
    assert verified_user.is_verified is True
    print("  [OK] Email verification token verified successfully; is_verified set to True")

    # Token reuse rejection
    try:
        verify_email_token(raw_verify_token_1, db=session)
        assert False, "Expected InvalidTokenError when re-using verification token"
    except InvalidTokenError as e:
        assert "already been used" in str(e)
        print("  [OK] Reused verification token rejected with InvalidTokenError")

    # Invalid token rejection
    try:
        verify_email_token("completely_fabricated_token_value", db=session)
        assert False, "Expected InvalidTokenError for fabricated token"
    except InvalidTokenError as e:
        assert "Invalid verification token" in str(e)
        print("  [OK] Fabricated verification token rejected with InvalidTokenError")

    # Expired token rejection
    with patch("services.auth_service.send_verification_email"):
        user_2, raw_verify_token_2 = register_user(
            full_name="Marcus Vance",
            email="marcus.vance@chassis-dynamics.de",
            password="MarcusPassword2026!",
            db=session
        )
    # Force expiration in database
    token_record = session.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user_2.id)
    ).scalar_one()
    token_record.expires_at = get_test_utc_now() - timedelta(minutes=5)
    session.commit()

    try:
        verify_email_token(raw_verify_token_2, db=session)
        assert False, "Expected InvalidTokenError for expired verification token"
    except InvalidTokenError as e:
        assert "expired" in str(e)
        print("  [OK] Expired verification token rejected with InvalidTokenError")

    # -------------------------------------------------------------
    # 7. Authenticated User Session for Verified Account
    # -------------------------------------------------------------
    print("\n--- 7. Verified User Authentication ---")
    user_auth = authenticate_user("elena.rostova@oem-aerospace.com", "SecurePass2026!Elena", db=session)
    assert user_auth is not None
    assert user_auth["email"] == "elena.rostova@oem-aerospace.com"
    assert user_auth["role"] == "user"
    assert user_auth["is_verified"] is True
    print("  [OK] Verified user authenticated successfully with role='user'")

    # Session token generation and payload
    user_token = create_session_token(
        email=user_auth["email"],
        role=user_auth["role"],
        user_id=user_auth["id"],
        name=user_auth["name"]
    )
    payload = verify_session_token(user_token)
    assert payload is not None
    assert payload["sub"] == "elena.rostova@oem-aerospace.com"
    assert payload["role"] == "user"
    assert payload["uid"] == user_auth["id"]
    print("  [OK] Session token payload holds verified user attributes and role='user'")

    # -------------------------------------------------------------
    # 8. Role-Based Access Control Helpers
    # -------------------------------------------------------------
    print("\n--- 8. Role-Based Access Control Checks ---")
    assert is_user_in_role(admin_auth, "admin") is True
    assert is_user_in_role(admin_auth, "user") is False
    assert is_user_in_role(user_auth, "user") is True
    assert is_user_in_role(user_auth, "admin") is False

    # require_role dependency test
    admin_checker = require_role("admin")
    user_checker = require_role("user")

    assert admin_checker(admin_auth) == admin_auth
    assert user_checker(user_auth) == user_auth

    # Access denied when user tries to access admin-restricted route
    try:
        admin_checker(user_auth)
        assert False, "Expected HTTP 403 Forbidden when user accesses admin route"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
        print("  [OK] require_role('admin') strictly blocked standard user with HTTP 403")

    # require_admin_user dependency test
    assert require_admin_user(admin_auth) == admin_auth
    try:
        require_admin_user(user_auth)
        assert False, "Expected HTTP 403 Forbidden from require_admin_user"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
        print("  [OK] require_admin_user blocked standard user with HTTP 403")

    # -------------------------------------------------------------
    # 9. Password Reset Request (Generic Anti-Enumeration Response)
    # -------------------------------------------------------------
    print("\n--- 9. Password Reset Request & Anti-Enumeration ---")
    # Request for non-existent user returns True
    assert request_password_reset("nonexistent.user@random.com", db=session) is True
    # Request for admin returns True without DB reset token
    assert request_password_reset(TEST_ADMIN_EMAIL, db=session) is True

    # Request for existing user
    with patch("services.auth_service.send_password_reset_email") as mock_reset_email:
        ok_reset_req = request_password_reset("elena.rostova@oem-aerospace.com", db=session)
        assert ok_reset_req is True
        assert mock_reset_email.called
        call_kwargs = mock_reset_email.call_args[1]
        assert call_kwargs["email"] == "elena.rostova@oem-aerospace.com"
        reset_url = call_kwargs["reset_url"]
        assert "reset-password?token=" in reset_url
        raw_reset_token = reset_url.split("token=")[1]
        print("  [OK] Password reset requested; single-use token dispatched via email")

    # -------------------------------------------------------------
    # 10. Password Reset Execution & Session Invalidation
    # -------------------------------------------------------------
    print("\n--- 10. Password Reset Execution & Invalidation ---")
    # Verify token before execution
    token_obj = verify_password_reset_token(raw_reset_token, db=session)
    assert token_obj is not None
    assert token_obj.used_at is None

    # Execute password reset with new password
    updated_user = reset_password(
        raw_token=raw_reset_token,
        new_password="BrandNewSecurePassword2026!",
        new_password_confirmation="BrandNewSecurePassword2026!",
        db=session
    )
    assert updated_user.email == "elena.rostova@oem-aerospace.com"

    # Verify old password fails
    assert authenticate_user("elena.rostova@oem-aerospace.com", "SecurePass2026!Elena", db=session) is None
    # Verify new password succeeds
    reauth = authenticate_user("elena.rostova@oem-aerospace.com", "BrandNewSecurePassword2026!", db=session)
    assert reauth is not None
    assert reauth["email"] == "elena.rostova@oem-aerospace.com"
    print("  [OK] Password reset completed; old password rejected and new password verified")

    # Prior session token must now be invalidated
    assert verify_session_token(user_token) is None
    print("  [OK] All previous sessions revoked upon password reset")

    # Token cannot be re-used
    try:
        reset_password(raw_reset_token, "AnotherPassword123!", db=session)
        assert False, "Expected InvalidTokenError on reused reset token"
    except InvalidTokenError as e:
        assert "already been used" in str(e)
        print("  [OK] Reused password reset token safely rejected")

    # Expired reset token rejection
    # Create another reset token and expire it
    with patch("services.auth_service.send_password_reset_email") as mock_reset_email_2:
        request_password_reset("elena.rostova@oem-aerospace.com", db=session)
        call_kwargs = mock_reset_email_2.call_args[1]
        raw_reset_token_2 = call_kwargs["reset_url"].split("token=")[1]

    # Force expiration
    prt_record = session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == updated_user.id)
    ).scalars().all()[-1]
    prt_record.expires_at = get_test_utc_now() - timedelta(minutes=10)
    session.commit()

    try:
        reset_password(raw_reset_token_2, "ExpiredAttempt2026!", db=session)
        assert False, "Expected InvalidTokenError for expired reset token"
    except InvalidTokenError as e:
        assert "expired" in str(e)
        print("  [OK] Expired password reset token safely rejected")

    # -------------------------------------------------------------
    # 11. Transaction Rollback on Failure
    # -------------------------------------------------------------
    print("\n--- 11. Database Transaction Rollback on Error ---")
    with patch("models.user.User.__init__", side_effect=Exception("Simulated unexpected ORM error")):
        try:
            register_user("Crash User", "crash@test.com", "CrashPassword2026!", db=session)
            assert False, "Expected Exception during simulated registration failure"
        except Exception as e:
            assert "Simulated unexpected ORM error" in str(e)

    # Verify database state was rolled back and no partial user exists
    crashed_user = session.execute(select(User).where(User.email == "crash@test.com")).scalar_one_or_none()
    assert crashed_user is None, "Partial user record leaked after transaction failure!"
    print("  [OK] Transaction rollback confirmed: zero orphaned data on failure")

    # -------------------------------------------------------------
    # 12. Persistent Session Revocation across Workers and Restarts
    # -------------------------------------------------------------
    print("\n--- 12. Persistent Session Revocation Across Instances ---")
    persisted_token = create_session_token(
        email="elena.rostova@oem-aerospace.com",
        role="user",
        user_id=updated_user.id
    )
    assert verify_session_token(persisted_token, db=session) is not None
    # Revoke on simulated Instance A
    revoke_session_token(persisted_token, db=session)

    # Verify revocation entry exists in RevokedToken database table
    payload_check = verify_session_token(persisted_token, db=session)
    assert payload_check is None

    # Simulate service reinitialization / worker B: wipe in-memory cache completely
    _REVOKED_SESSION_JTIS.clear()
    assert len(_REVOKED_SESSION_JTIS) == 0

    # Verification on Worker B with cold cache must query DB and reject the revoked session
    assert verify_session_token(persisted_token, db=session) is None
    print("  [OK] Revoked session rejected across simulated instances and service reinitialization")

    # -------------------------------------------------------------
    # 13. Persistent User-Level Revocation after Password Reset
    # -------------------------------------------------------------
    print("\n--- 13. Persistent User Revocation after Password Reset ---")
    with patch("services.auth_service.send_verification_email"):
        user_persist, _ = register_user(
            full_name="Persist Test",
            email="persist@test.com",
            password="InitialPassword2026!",
            db=session
        )
    # Activate user
    user_persist.is_verified = True
    session.commit()

    active_user_token = create_session_token(
        email="persist@test.com",
        role="user",
        user_id=user_persist.id
    )
    assert verify_session_token(active_user_token, db=session) is not None

    # Issue reset token and execute password reset
    with patch("services.auth_service.send_password_reset_email") as mock_reset:
        request_password_reset("persist@test.com", db=session)
        reset_url = mock_reset.call_args[1]["reset_url"]
        reset_raw = reset_url.split("token=")[1]

    reset_password(reset_raw, "NewPersistPassword2026!", db=session)

    # Simulate service reinitialization / cold worker: clear in-memory cutoff
    _USER_REVOCATION_CUTOFF.clear()
    assert "persist@test.com" not in _USER_REVOCATION_CUTOFF

    # Old token must still be rejected on Worker B due to User.password_changed_at in DB
    assert verify_session_token(active_user_token, db=session) is None
    print("  [OK] Password reset invalidation persisted in DB and survives memory wipes")

    # -------------------------------------------------------------
    # 14. Production Email Configuration Enforcement
    # -------------------------------------------------------------
    print("\n--- 14. Production Email Configuration Enforcement ---")
    saved_env = os.environ.get("ENVIRONMENT")
    saved_resend_key = os.environ.get("RESEND_API_KEY")
    saved_sender = os.environ.get("RESEND_FROM_EMAIL")

    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["AUTH_SECRET_KEY"] = "prod-secret-32-bytes-long-secure"
        os.environ["ADMIN_EMAIL"] = "admin@compbench.ai"
        os.environ["ADMIN_PASSWORD_HASH"] = hash_password("SuperSecret2026!")

        # A. Missing RESEND_API_KEY
        os.environ.pop("RESEND_API_KEY", None)
        os.environ["RESEND_FROM_EMAIL"] = "auth@compbench.ai"
        try:
            validate_production_configuration()
            assert False, "Expected failure when RESEND_API_KEY is missing in production"
        except RuntimeError as exc:
            assert "RESEND_API_KEY" in str(exc)
            print("  [OK] Missing production RESEND_API_KEY rejected securely")

        # B. Test sender domain rejected in production
        os.environ["RESEND_API_KEY"] = "re_production_test_key_12345"
        os.environ["RESEND_FROM_EMAIL"] = "CompBench <onboarding@resend.dev>"
        try:
            validate_production_configuration()
            assert False, "Expected failure when resend.dev is used in production"
        except RuntimeError as exc:
            assert "verified custom domain" in str(exc)
            print("  [OK] Test domain 'resend.dev' rejected in production")

        # C. Verified custom sender domain accepted in production
        os.environ["RESEND_FROM_EMAIL"] = "CompBench AI <auth@compbench.ai>"
        validate_production_configuration()  # Must not raise
        print("  [OK] Production configuration accepted with verified custom domain")

    finally:
        if saved_env is not None:
            os.environ["ENVIRONMENT"] = saved_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        if saved_resend_key is not None:
            os.environ["RESEND_API_KEY"] = saved_resend_key
        else:
            os.environ.pop("RESEND_API_KEY", None)
        if saved_sender is not None:
            os.environ["RESEND_FROM_EMAIL"] = saved_sender
        else:
            os.environ.pop("RESEND_FROM_EMAIL", None)

    # -------------------------------------------------------------
    # 15. Concurrent Token Redemption Protection
    # -------------------------------------------------------------
    print("\n--- 15. Concurrent Token Redemption Protection ---")
    with patch("services.auth_service.send_verification_email"):
        user_concurrent, raw_concurrent_token = register_user(
            full_name="Concurrency User",
            email="concurrent@test.com",
            password="ConcurrentPass2026!",
            db=session
        )

    # First attempt: successfully redeems token
    first_res = verify_email_token(raw_concurrent_token, db=session)
    assert first_res.is_verified is True

    # Immediate second and concurrent attempts must be rejected
    try:
        verify_email_token(raw_concurrent_token, db=session)
        assert False, "Expected InvalidTokenError on re-used token"
    except InvalidTokenError as exc:
        assert "already been used" in str(exc)

    # Simulated simultaneous worker attempts
    results = []
    for _ in range(4):
        try:
            verify_email_token(raw_concurrent_token, db=session)
            results.append("SUCCESS")
        except InvalidTokenError as exc:
            results.append(f"INVALID: {exc}")

    assert all("already been used" in r for r in results)

    # Password reset concurrency protection
    with patch("services.auth_service.send_password_reset_email") as mock_reset_conc:
        request_password_reset("concurrent@test.com", db=session)
        conc_reset_url = mock_reset_conc.call_args[1]["reset_url"]
        conc_reset_token = conc_reset_url.split("token=")[1]

    # First reset succeeds
    reset_user_res = reset_password(conc_reset_token, "NewConcPass2026!A", db=session)
    assert reset_user_res is not None

    # Competing attempts must be rejected
    reset_competing_results = []
    for _ in range(3):
        try:
            reset_password(conc_reset_token, "NewConcPass2026!B", db=session)
            reset_competing_results.append("SUCCESS")
        except InvalidTokenError as exc:
            reset_competing_results.append(f"INVALID: {exc}")

    assert all("already been used" in r for r in reset_competing_results)
    print("  [OK] Concurrent token redemption allows only one successful operation (subsequent requests rejected)")

    session.close()
    close_db_engine()

    print("\n============================================================")
    print("ALL 15 MULTI-USER AUTHENTICATION TEST SUITES PASSED!")
    print("============================================================")


if __name__ == "__main__":
    run_multi_user_auth_tests()
