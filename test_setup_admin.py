"""
Comprehensive Test Suite for Administrator Setup Script (setup_admin.py).

Validates:
1. Automated admin provisioning with Argon2id password hashing.
2. Authentication secret key generation.
3. Preservation of existing environment variables in .env.
4. Overwrite confirmation guard (prevents accidental credential replacement).
5. Password length and email format validation.
6. Zero leakage: plain-text password is never stored in .env.
7. End-to-end integration: provisioned credentials authenticate with auth_service.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from setup_admin import provision_admin, parse_env_file, update_env_file
from services.auth_service import verify_password, authenticate_user


def test_setup_admin_suite():
    print("============================================================")
    print("COMPBENCH AI: SETUP ADMIN SCRIPT TEST SUITE")
    print("============================================================")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_env = Path(tmp_dir) / ".env"

        # ---------------------------------------------------------
        # 1. Initial Provisioning on Clean File
        # ---------------------------------------------------------
        print("\n--- 1. Clean File Provisioning ---")
        test_email = "lead_engineer@compbench.ai"
        test_password = "SecureAutomotive2026!"

        ok, msg = provision_admin(
            email=test_email,
            password=test_password,
            env_file=tmp_env,
            force_overwrite=False
        )
        assert ok is True, f"Provisioning failed: {msg}"
        assert tmp_env.exists(), ".env was not created"

        parsed = parse_env_file(tmp_env)
        assert parsed["ADMIN_EMAIL"] == test_email
        assert parsed["ADMIN_PASSWORD_HASH"].startswith("$argon2id$")
        assert len(parsed["AUTH_SECRET_KEY"]) >= 32
        assert test_password not in tmp_env.read_text(encoding="utf-8"), "Plaintext password leaked into .env!"

        # Verify password against generated hash
        assert verify_password(test_password, parsed["ADMIN_PASSWORD_HASH"]) is True
        assert verify_password("WrongPassword!", parsed["ADMIN_PASSWORD_HASH"]) is False
        print("  [OK] Clean provisioning created .env with valid Argon2id hash and secret key")

        # ---------------------------------------------------------
        # 2. Overwrite Protection Guard
        # ---------------------------------------------------------
        print("\n--- 2. Overwrite Protection Guard ---")
        ok_overwrite, msg_overwrite = provision_admin(
            email="intruder@compbench.ai",
            password="AnotherPassword123!",
            env_file=tmp_env,
            force_overwrite=False
        )
        assert ok_overwrite is False, "Expected overwrite guard to reject without confirmation"
        assert "Overwrite confirmation required" in msg_overwrite

        # Verify previous credentials are untouched
        parsed_after_reject = parse_env_file(tmp_env)
        assert parsed_after_reject["ADMIN_EMAIL"] == test_email
        print("  [OK] Overwrite guard protected existing credentials when confirmation was False")

        # Now test with force_overwrite=True
        ok_force, msg_force = provision_admin(
            email="updated_admin@compbench.ai",
            password="NewSecurePassword2026!",
            env_file=tmp_env,
            force_overwrite=True
        )
        assert ok_force is True, f"Forced overwrite failed: {msg_force}"
        parsed_forced = parse_env_file(tmp_env)
        assert parsed_forced["ADMIN_EMAIL"] == "updated_admin@compbench.ai"
        assert verify_password("NewSecurePassword2026!", parsed_forced["ADMIN_PASSWORD_HASH"]) is True
        print("  [OK] Forced overwrite successfully updated admin credentials")

        # ---------------------------------------------------------
        # 3. Preservation of Existing Environment Settings
        # ---------------------------------------------------------
        print("\n--- 3. Preservation of Existing Environment Variables ---")
        custom_env = Path(tmp_dir) / "custom.env"
        initial_content = (
            "# Existing Configuration\n"
            "ENVIRONMENT=development\n"
            "GEMINI_API_KEY=ai_studio_secret_test_key_12345\n"
            "GEMINI_MODEL=gemini-2.5-flash\n"
            "SESSION_DURATION_HOURS=12\n"
            "ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n"
        )
        custom_env.write_text(initial_content, encoding="utf-8")

        ok_preserve, _ = provision_admin(
            email="lead@compbench.ai",
            password="PreservePassword2026!",
            env_file=custom_env
        )
        assert ok_preserve is True

        parsed_custom = parse_env_file(custom_env)
        assert parsed_custom["GEMINI_API_KEY"] == "ai_studio_secret_test_key_12345"
        assert parsed_custom["GEMINI_MODEL"] == "gemini-2.5-flash"
        assert parsed_custom["SESSION_DURATION_HOURS"] == "12"
        assert parsed_custom["ALLOWED_ORIGINS"] == "http://localhost:3000,http://127.0.0.1:3000"
        assert parsed_custom["ADMIN_EMAIL"] == "lead@compbench.ai"
        assert parsed_custom["ADMIN_PASSWORD_HASH"].startswith("$argon2id$")
        print("  [OK] Existing variables (GEMINI_API_KEY, SESSION_DURATION_HOURS, etc.) perfectly preserved")

        # ---------------------------------------------------------
        # 4. Input Validation (Password length and Email format)
        # ---------------------------------------------------------
        print("\n--- 4. Input Validation ---")
        ok_short, msg_short = provision_admin("valid@email.com", "short", env_file=tmp_env, force_overwrite=True)
        assert ok_short is False
        assert "at least 8 characters" in msg_short

        ok_bad_email, msg_bad_email = provision_admin("not-an-email", "LongPassword123!", env_file=tmp_env, force_overwrite=True)
        assert ok_bad_email is False
        assert "Invalid email" in msg_bad_email
        print("  [OK] Validation correctly rejected short passwords and invalid email formats")

        # ---------------------------------------------------------
        # 5. Integration with auth_service.authenticate_user
        # ---------------------------------------------------------
        print("\n--- 5. End-to-End Authentication Verification ---")
        # Temporarily point environment variables to custom_env values
        os.environ["ADMIN_EMAIL"] = parsed_custom["ADMIN_EMAIL"]
        os.environ["ADMIN_PASSWORD_HASH"] = parsed_custom["ADMIN_PASSWORD_HASH"]
        os.environ["AUTH_SECRET_KEY"] = parsed_custom["AUTH_SECRET_KEY"]

        user = authenticate_user("lead@compbench.ai", "PreservePassword2026!")
        assert user is not None, "authenticate_user failed with provisioned credentials"
        assert user["email"] == "lead@compbench.ai"
        assert user["role"] == "admin"

        # Bad password must be rejected
        assert authenticate_user("lead@compbench.ai", "WrongPassword") is None
        print("  [OK] Provisioned credentials successfully authenticated against auth_service")

    print("\n============================================================")
    print("ALL SETUP ADMIN TESTS PASSED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    test_setup_admin_suite()

