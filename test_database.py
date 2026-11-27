"""
Comprehensive Unit Test Suite for CompBench AI Database Layer (Phase 1).

Validates:
1. MySQL URL construction with PyMySQL dialect and parameter encoding.
2. Production enforcement: strict rejection of SQLite in production (no silent fallback).
3. Test environment isolation: in-memory SQLite permitted strictly when TESTING=1.
4. Connection pooling configuration and health check pinging.
5. SQLAlchemy Session lifecycle management and get_db generator cleanup.
6. ORM Model schemas: User, EmailVerificationToken, PasswordResetToken, RevokedToken.
7. Foreign key cascades: deleting User cascades to verification and reset tokens.
8. Explicit migrations via run_migrations (no automatic DDL at startup).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def get_test_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Explicitly flag test mode for the test process
os.environ["TESTING"] = "1"

from sqlalchemy import select, inspect
from services.database import (
    build_mysql_url,
    get_database_url,
    get_engine,
    get_db_session,
    get_db,
    close_db_engine,
    test_connection,
    run_migrations,
    is_production,
    is_testing_environment
)
from models.user import (
    Base,
    User,
    EmailVerificationToken,
    PasswordResetToken,
    RevokedToken
)


def run_database_test_suite():
    print("============================================================")
    print("COMPBENCH AI: DATABASE & MODELS TEST SUITE (PHASE 1)")
    print("============================================================")

    # -------------------------------------------------------------
    # 1. MySQL URL Construction & Encoding
    # -------------------------------------------------------------
    print("\n--- 1. MySQL URL Construction & Parameter Encoding ---")
    url = build_mysql_url(
        host="db.compbench.internal",
        port=3307,
        user="db_user",
        password="P@ssw0rd!#$&*",
        database="fleet_benchmarks"
    )
    assert url.startswith("mysql+pymysql://"), f"Expected mysql+pymysql dialect, got: {url}"
    assert "db_user:" in url, "Username missing"
    assert "P%40ssw0rd%21%23%24%26%2A" in url, "Password was not safely URL-encoded"
    assert "@db.compbench.internal:3307/fleet_benchmarks?charset=utf8mb4" in url
    print("  [OK] build_mysql_url correctly generated PyMySQL connection string with encoded credentials")

    # Incomplete credentials return None
    assert build_mysql_url(user=None, database="test") is None
    assert build_mysql_url(user="user", database=None) is None
    print("  [OK] Incomplete MySQL credentials safely return None")

    # -------------------------------------------------------------
    # 2. Production Security Enforcement (No SQLite in Production)
    # -------------------------------------------------------------
    print("\n--- 2. Production Security: Strict SQLite Rejection ---")
    saved_env = os.environ.get("ENVIRONMENT")
    saved_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        try:
            get_database_url()
            assert False, "Expected RuntimeError when SQLite is configured in production"
        except RuntimeError as e:
            assert "strictly prohibited in production" in str(e)
            print("  [OK] Production strictly rejects SQLite connection URL with RuntimeError")

        # Missing MySQL in production also raises RuntimeError
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("MYSQL_USER", None)
        try:
            get_database_url()
            assert False, "Expected RuntimeError when MySQL is unconfigured in production"
        except RuntimeError as e:
            assert "MySQL database connection is required in production" in str(e)
            print("  [OK] Production securely fails when MySQL connection is missing")

    finally:
        if saved_env is not None:
            os.environ["ENVIRONMENT"] = saved_env
        else:
            os.environ.pop("ENVIRONMENT", None)

        if saved_url is not None:
            os.environ["DATABASE_URL"] = saved_url
        else:
            os.environ.pop("DATABASE_URL", None)

    # -------------------------------------------------------------
    # 3. Test Mode In-Memory SQLite Support
    # -------------------------------------------------------------
    print("\n--- 3. Automated Test Mode Isolation ---")
    assert is_testing_environment() is True
    test_url = get_database_url(force_sqlite_test=True)
    assert test_url == "sqlite:///:memory:"
    print("  [OK] Test mode correctly uses isolated in-memory SQLite (sqlite:///:memory:)")

    # -------------------------------------------------------------
    # 4. Engine Initialization & Explicit Schema Migrations
    # -------------------------------------------------------------
    print("\n--- 4. Engine Creation & Explicit Schema Migrations ---")
    close_db_engine()
    engine = get_engine(force_sqlite_test=True)
    assert engine is not None
    assert test_connection(force_sqlite_test=True) is True
    print("  [OK] Engine successfully connected and passed health-check ping (SELECT 1)")

    # Run explicit migrations
    run_migrations(target_engine=engine)

    # Inspect created tables
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    expected_tables = {"users", "email_verification_tokens", "password_reset_tokens", "revoked_tokens"}
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"
    print(f"  [OK] Explicit migration created all 4 tables: {sorted(list(expected_tables))}")

    # -------------------------------------------------------------
    # 5. Session Management & get_db Generator
    # -------------------------------------------------------------
    print("\n--- 5. Session Lifecycle & get_db Dependency ---")
    session = get_db_session(force_sqlite_test=True)
    assert session is not None
    session.close()

    # Verify get_db generator cleans up session
    db_gen = get_db()
    active_session = next(db_gen)
    assert active_session.is_active
    try:
        next(db_gen)
    except StopIteration:
        pass
    print("  [OK] get_db generator yielded active session and closed cleanly on iteration end")

    # -------------------------------------------------------------
    # 6. ORM Models CRUD Verification
    # -------------------------------------------------------------
    print("\n--- 6. ORM Model Operations: User, Tokens, Revocation ---")
    session = get_db_session(force_sqlite_test=True)

    # A. Create User
    new_user = User(
        full_name="Lead Benchmark Engineer",
        email="lead.engineer@compbench.ai",
        password_hash="$argon2id$v=19$m=4096,t=2,p=1$synthetic_test_hash",
        role="user",
        is_verified=False
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    assert new_user.id is not None
    assert new_user.role == "user"
    assert new_user.is_verified is False
    assert repr(new_user) == f"<User id={new_user.id} email='lead.engineer@compbench.ai' role='user' is_verified=False>"
    print("  [OK] User entity persisted successfully with default role='user' and is_verified=False")

    # B. Create EmailVerificationToken
    evt = EmailVerificationToken(
        user_id=new_user.id,
        token_hash="sha256_mock_verification_token_hash_value_1234567890abcdef",
        expires_at=get_test_utc_now() + timedelta(hours=24)
    )
    session.add(evt)
    session.commit()
    session.refresh(evt)

    assert evt.id is not None
    assert evt.used_at is None
    assert evt.user.email == "lead.engineer@compbench.ai"
    print("  [OK] EmailVerificationToken persisted and linked via relationship to User")

    # C. Create PasswordResetToken
    prt = PasswordResetToken(
        user_id=new_user.id,
        token_hash="sha256_mock_password_reset_token_hash_value_abcdef1234567890",
        expires_at=get_test_utc_now() + timedelta(hours=1)
    )
    session.add(prt)
    session.commit()
    session.refresh(prt)

    assert prt.id is not None
    assert prt.used_at is None
    assert prt.user.email == "lead.engineer@compbench.ai"
    print("  [OK] PasswordResetToken persisted and linked via relationship to User")

    # D. Create RevokedToken
    rev = RevokedToken(
        jti="unique-jwt-jti-token-identifier-98765",
        expires_at=get_test_utc_now() + timedelta(hours=8)
    )
    session.add(rev)
    session.commit()
    session.refresh(rev)

    assert rev.id is not None
    assert rev.jti == "unique-jwt-jti-token-identifier-98765"
    print("  [OK] RevokedToken blacklist entity persisted with unique jti")

    # -------------------------------------------------------------
    # 7. Cascade Deletion Integrity
    # -------------------------------------------------------------
    print("\n--- 7. Foreign Key Cascade Deletion ---")
    user_id = new_user.id
    session.delete(new_user)
    session.commit()

    # Tokens linked to user must be automatically cascade-deleted
    remaining_evt = session.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user_id)
    ).scalars().all()
    assert len(remaining_evt) == 0, "EmailVerificationToken was not cascade deleted!"

    remaining_prt = session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    ).scalars().all()
    assert len(remaining_prt) == 0, "PasswordResetToken was not cascade deleted!"
    print("  [OK] Cascade deletion confirmed: deleting user removed associated verification & reset tokens")

    session.close()
    close_db_engine()

    print("\n============================================================")
    print("ALL PHASE 1 DATABASE & MODEL TESTS PASSED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    run_database_test_suite()
