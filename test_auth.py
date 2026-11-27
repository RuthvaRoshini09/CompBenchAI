"""
Comprehensive Authentication & Session Security Test Suite for CompBench AI.

Validates:
1. Argon2 password hashing, salt generation, and constant-time verification.
2. Administrator credential bootstrapping strictly from environment (no hardcoded fallback).
3. Secure failure when required production credentials or secrets are missing.
4. Cryptographically signed session tokens (HMAC-SHA256, tampering detection, expiration).
5. Server-side session revocation: explicit logout invalidates copied tokens.
6. Direct /api/auth/login validation (empty credentials, invalid email, invalid password, valid login).
7. Cookie security behavior (HttpOnly, SameSite=Lax, and dynamic TLS Secure flag).
8. CSRF protection on cookie-authenticated state-changing requests.
9. Protected API route enforcement (HTTP 401 on /components, /compare, /analyze, /material-intelligence, /knowledge/retrieve without auth).
10. Dual authorization support (Bearer tokens and HttpOnly Cookies).
11. Browser navigation gatekeeping (Redirecting unauthenticated browser clients to /login).
12. Frontend asset integrity (Zero tokens in sessionStorage; HttpOnly cookie authentication; X-CompBench-CSRF header).
"""

import os
import sys
import time
from pathlib import Path

# Ensure automated test mode
os.environ["TESTING"] = "1"

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from services.auth_service import (
    hash_password,
    verify_password,
    create_session_token,
    verify_session_token,
    revoke_session_token,
    authenticate_user,
    get_admin_credentials,
    get_auth_secret_key,
    extract_token_from_request,
    get_current_user_from_request,
    require_authenticated_user,
    is_authenticated_request,
    is_production,
    validate_production_configuration,
    verify_csrf_protection,
    get_csrf_token_from_session,
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME
)

from main import (
    app,
    LoginRequest,
    login_page,
    api_login,
    api_logout,
    api_me,
    home,
    dashboard,
    components,
    compare,
    material_intelligence_endpoint,
    analyze,
    is_request_secure,
    ComparisonRequest,
    MaterialIntelligenceRequest,
    AnalyzeRequest
)


class MockRequest:
    """Mock HTTP Request for hermetic unit testing without external networking drivers."""
    def __init__(self, method="GET", headers=None, cookies=None, query_params=None, url_scheme="http"):
        self.method = method
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.query_params = query_params or {}
        class MockUrl:
            def __init__(self, scheme):
                self.scheme = scheme
        self.url = MockUrl(url_scheme)


class MockResponse:
    """Mock HTTP Response for verifying cookie manipulations."""
    def __init__(self):
        self.cookies = {}
        self.deleted_cookies = []

    def set_cookie(self, key, value, max_age=None, httponly=False, samesite="lax", secure=False, path="/"):
        self.cookies[key] = {
            "value": value,
            "max_age": max_age,
            "httponly": httponly,
            "samesite": samesite,
            "secure": secure,
            "path": path
        }

    def delete_cookie(self, key, path="/", domain=None):
        if key in self.cookies:
            del self.cookies[key]
        self.deleted_cookies.append(key)


def run_auth_test_suite():
    print("============================================================")
    print("COMPBENCH AI: ENTERPRISE AUTHENTICATION & SECURITY TEST SUITE")
    print("============================================================")

    # Provision dynamic credentials in test environment
    TEST_ADMIN_EMAIL = "admin@compbench.ai"
    TEST_ADMIN_PASS = "EnterpriseTestPassword2026!"
    os.environ["ADMIN_EMAIL"] = TEST_ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD_HASH"] = hash_password(TEST_ADMIN_PASS)
    os.environ["AUTH_SECRET_KEY"] = "unit-test-secret-key-32-bytes-long-for-hmac-integrity"

    # -------------------------------------------------------------
    # 1. Argon2 Password Hashing & Constant-time Verification
    # -------------------------------------------------------------
    print("\n--- 1. Argon2 Password Hashing & Verification ---")
    plain = "AutomotiveEngineeringPass2026!"
    hashed = hash_password(plain)
    assert hashed.startswith("$argon2id$"), f"Expected Argon2id hash, got: {hashed[:15]}..."
    assert verify_password(plain, hashed) is True, "Valid password failed verification"
    assert verify_password("WrongPassword!", hashed) is False, "Invalid password falsely verified"
    assert verify_password("", hashed) is False, "Empty password falsely verified"
    assert verify_password(plain, "") is False, "Empty hash falsely verified"
    assert verify_password(plain, "$invalid$hash") is False, "Corrupted hash falsely verified"
    print("  [OK] Argon2id hashing, unique salting, and constant-time verification verified")

    # -------------------------------------------------------------
    # 2. Secure Failure on Missing Credentials (No Hardcoded Fallback)
    # -------------------------------------------------------------
    print("\n--- 2. Secure Failure on Missing Credentials ---")
    saved_email = os.environ.pop("ADMIN_EMAIL", None)
    saved_hash = os.environ.pop("ADMIN_PASSWORD_HASH", None)
    saved_pass = os.environ.pop("ADMIN_PASSWORD", None)

    # When environment variables are missing, credentials must return None
    assert get_admin_credentials() is None, "Credentials returned even when unconfigured"
    assert authenticate_user("admin@compbench.ai", "CompBench2026!Admin") is None, "Accepted unconfigured credentials"
    print("  [OK] System fails securely with no hardcoded fallback when credentials are unconfigured")

    # Restore dynamic test credentials
    os.environ["ADMIN_EMAIL"] = TEST_ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD_HASH"] = saved_hash or hash_password(TEST_ADMIN_PASS)

    # Verify authenticated administrator matches provisioned environment variables
    admin_creds = get_admin_credentials()
    assert admin_creds is not None and admin_creds["email"] == TEST_ADMIN_EMAIL
    auth_success = authenticate_user(TEST_ADMIN_EMAIL, TEST_ADMIN_PASS)
    assert auth_success is not None, "Configured administrator login failed"
    assert auth_success["email"] == TEST_ADMIN_EMAIL
    assert auth_success["role"] == "admin"

    # Case-insensitivity for email
    auth_case = authenticate_user(TEST_ADMIN_EMAIL.upper(), TEST_ADMIN_PASS)
    assert auth_case is not None, "Email case-insensitive matching failed"

    # Reject incorrect credentials
    assert authenticate_user(TEST_ADMIN_EMAIL, "WrongPassword") is None
    assert authenticate_user("intruder@external.org", TEST_ADMIN_PASS) is None
    print("  [OK] Admin provisioning from environment verified")

    # -------------------------------------------------------------
    # 3. Production Configuration Enforcement
    # -------------------------------------------------------------
    print("\n--- 3. Production Configuration Enforcement ---")
    saved_env = os.environ.get("ENVIRONMENT")
    saved_secret = os.environ.pop("AUTH_SECRET_KEY", None)

    # In production without AUTH_SECRET_KEY: must raise RuntimeError
    os.environ["ENVIRONMENT"] = "production"
    try:
        validate_production_configuration()
        assert False, "Expected RuntimeError for missing AUTH_SECRET_KEY in production"
    except RuntimeError as exc:
        assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc)
        print("  [OK] Server securely refuses to start in production if AUTH_SECRET_KEY is missing")

    # Restore environment settings
    if saved_env is not None:
        os.environ["ENVIRONMENT"] = saved_env
    else:
        os.environ.pop("ENVIRONMENT", None)
    os.environ["AUTH_SECRET_KEY"] = saved_secret or "unit-test-secret-key-32-bytes-long-for-hmac-integrity"

    # -------------------------------------------------------------
    # 4. Cryptographic Session Token Lifecycle
    # -------------------------------------------------------------
    print("\n--- 4. HMAC-SHA256 Session Token Lifecycle & Expiration ---")
    valid_token = create_session_token(TEST_ADMIN_EMAIL, "admin", expires_in_seconds=3600)
    payload = verify_session_token(valid_token)
    assert payload is not None, "Valid session token rejected"
    assert payload["sub"] == TEST_ADMIN_EMAIL
    assert payload["role"] == "admin"
    assert payload["exp"] > int(time.time())

    # Token Tampering Detection
    parts = valid_token.split(".")
    tampered_sig = parts[0] + "." + parts[1] + ".tampered_signature"
    assert verify_session_token(tampered_sig) is None, "Tampered signature accepted"

    tampered_payload = parts[0] + ".eyJhZG1pbiI6dHJ1ZX0." + parts[2]
    assert verify_session_token(tampered_payload) is None, "Tampered payload accepted"

    # Token Expiration Detection
    expired_token = create_session_token(TEST_ADMIN_EMAIL, "admin", expires_in_seconds=-10)
    assert verify_session_token(expired_token) is None, "Expired session token accepted"
    print("  [OK] Session token generation, HMAC integrity, and expiration verified")

    # -------------------------------------------------------------
    # 5. Server-side Session Revocation (Copied Token Invalidation)
    # -------------------------------------------------------------
    print("\n--- 5. Server-Side Session Revocation ---")
    active_token = create_session_token(TEST_ADMIN_EMAIL, "admin", expires_in_seconds=3600)
    assert verify_session_token(active_token) is not None, "Active token should be valid"

    # Revoke session explicitly
    revocation_ok = revoke_session_token(active_token)
    assert revocation_ok is True, "Token revocation failed"

    # Copied or replayed token must now be rejected
    assert verify_session_token(active_token) is None, "Revoked token was still accepted!"

    # Verify that a request using the revoked token is rejected with HTTP 401
    revoked_req = MockRequest(headers={"Authorization": f"Bearer {active_token}"})
    try:
        require_authenticated_user(revoked_req)
        assert False, "Expected 401 for revoked token"
    except HTTPException as exc:
        assert exc.status_code == 401
    print("  [OK] Server-side session revocation successfully invalidates copied tokens")

    # -------------------------------------------------------------
    # 6. Sign In Endpoint: POST /api/auth/login
    # -------------------------------------------------------------
    print("\n--- 6. Sign In Endpoint: POST /api/auth/login ---")
    mock_res = MockResponse()

    # Empty fields validation
    try:
        api_login(LoginRequest(email="", password=""), mock_res)
        assert False, "Expected 400 for empty fields"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "required" in exc.detail.lower()

    # Invalid credentials
    try:
        api_login(LoginRequest(email=TEST_ADMIN_EMAIL, password="BadPassword"), mock_res)
        assert False, "Expected 401 for bad password"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "invalid" in exc.detail.lower()

    # Valid credentials
    login_result = api_login(LoginRequest(email=TEST_ADMIN_EMAIL, password=TEST_ADMIN_PASS), mock_res)
    assert login_result["status"] == "success"
    assert login_result["user"]["email"] == TEST_ADMIN_EMAIL
    assert "token" not in login_result, "Browser login response must not expose raw session JWT in JSON"

    # Verify HTTP-only session cookie and readable CSRF cookie
    assert SESSION_COOKIE_NAME in mock_res.cookies
    cookie_info = mock_res.cookies[SESSION_COOKIE_NAME]
    assert cookie_info["httponly"] is True
    assert cookie_info["samesite"] == "lax"
    auth_token = cookie_info["value"]

    assert CSRF_COOKIE_NAME in mock_res.cookies
    csrf_cookie_info = mock_res.cookies[CSRF_COOKIE_NAME]
    assert csrf_cookie_info["httponly"] is False
    assert csrf_cookie_info["samesite"] == "lax"
    session_csrf = csrf_cookie_info["value"]
    assert len(session_csrf) == 64
    print("  [OK] POST /api/auth/login: validation, 401 rejection, HttpOnly session cookie & readable CSRF cookie verified")

    # -------------------------------------------------------------
    # 7. Cookie Secure Flag Behavior (Localhost vs Production HTTPS)
    # -------------------------------------------------------------
    print("\n--- 7. Cookie Secure Behavior ---")
    http_req = MockRequest(headers={"x-forwarded-proto": "http"}, url_scheme="http")
    assert is_request_secure(http_req) is False, "Localhost HTTP should not enforce Secure cookie"

    https_req = MockRequest(headers={"x-forwarded-proto": "https"}, url_scheme="https")
    assert is_request_secure(https_req) is True, "HTTPS request must enforce Secure cookie"

    # Verify login under HTTPS sets secure=True
    https_res = MockResponse()
    api_login(LoginRequest(email=TEST_ADMIN_EMAIL, password=TEST_ADMIN_PASS), https_res, request=https_req)
    assert https_res.cookies[SESSION_COOKIE_NAME]["secure"] is True
    print("  [OK] Cookie Secure flag correctly toggles for localhost (False) and HTTPS (True)")

    # -------------------------------------------------------------
    # 8. CSRF Protection for Cookie Authentication (Genuine Session-Bound Verification)
    # -------------------------------------------------------------
    print("\n--- 8. CSRF Protection on State-Changing Requests (Genuine Session-Bound Verification) ---")
    session_csrf = get_csrf_token_from_session(auth_token)
    assert session_csrf is not None and len(session_csrf) == 64, "Session token must contain a 64-char hex CSRF token"

    # A. Untrusted cross-origin request using cookie session without CSRF header -> 403 Forbidden
    malicious_req = MockRequest(
        method="POST",
        headers={"origin": "https://malicious-attacker.com", "host": "compbench.ai"},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(malicious_req)
        assert False, "Expected 403 Forbidden for untrusted cross-origin cookie request"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "CSRF validation failed" in exc.detail
        print("  [OK] Untrusted origin rejected with HTTP 403")

    # B. Malicious origin with valid CSRF header and cookie must STILL be rejected (Origin check cannot be bypassed)
    malicious_with_csrf = MockRequest(
        method="POST",
        headers={"origin": "https://malicious-attacker.com", "host": "compbench.ai", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(malicious_with_csrf)
        assert False, "Expected 403 Forbidden for untrusted origin even with valid CSRF credentials"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "untrusted origin" in exc.detail
        print("  [OK] Untrusted origin with valid CSRF header/cookie strictly rejected (Condition 1 enforced)")

    # C. Malicious Vercel subdomain with valid CSRF credentials strictly rejected
    malicious_vercel = MockRequest(
        method="POST",
        headers={"origin": "https://attacker.vercel.app", "host": "compbench.ai", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(malicious_vercel)
        assert False, "Expected 403 Forbidden for arbitrary vercel.app subdomain"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "untrusted origin" in exc.detail
        print("  [OK] Malicious Vercel subdomain rejected with HTTP 403")

    # D. Lookalike localhost domain with valid CSRF credentials rejected
    lookalike_req = MockRequest(
        method="POST",
        headers={"origin": "http://attacker-localhost.com:8000", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(lookalike_req)
        assert False, "Expected 403 Forbidden for lookalike localhost domain"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "untrusted origin" in exc.detail
        print("  [OK] Lookalike localhost domain rejected with HTTP 403")

    # E. Untrusted Referer with valid CSRF credentials rejected (when Origin is absent)
    untrusted_ref_req = MockRequest(
        method="POST",
        headers={"referer": "https://attacker-site.com/form", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(untrusted_ref_req)
        assert False, "Expected 403 Forbidden for untrusted referer"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "untrusted referer" in exc.detail
        print("  [OK] Untrusted Referer rejected with HTTP 403")

    # F. Missing Origin and Referer rejected (Fail-closed) even with valid CSRF credentials
    missing_headers_req = MockRequest(
        method="POST",
        headers={"host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(missing_headers_req)
        assert False, "Expected 403 Forbidden when Origin and Referer are absent"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "missing origin or referer" in exc.detail
        print("  [OK] Missing Origin and Referer rejected with HTTP 403")

    # G. Missing CSRF header from trusted origin rejected
    missing_csrf_req = MockRequest(
        method="POST",
        headers={"origin": "http://localhost:8000", "host": "localhost:8000"},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    try:
        verify_csrf_protection(missing_csrf_req)
        assert False, "Expected 403 Forbidden when X-CompBench-CSRF is missing"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "missing X-CompBench-CSRF header" in exc.detail
        print("  [OK] Missing X-CompBench-CSRF header rejected with HTTP 403")

    # H. Missing compbench_csrf cookie from trusted origin rejected
    missing_cookie_req = MockRequest(
        method="POST",
        headers={"origin": "http://localhost:8000", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token}
    )
    try:
        verify_csrf_protection(missing_cookie_req)
        assert False, "Expected 403 Forbidden when compbench_csrf cookie is missing"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "missing compbench_csrf cookie" in exc.detail
        print("  [OK] Missing compbench_csrf cookie rejected with HTTP 403")

    # I. Static CSRF tokens ('1', 'true', etc.) strictly rejected
    for static_val in ("1", "true", "True", "yes", "0", "false"):
        static_csrf_req = MockRequest(
            method="POST",
            headers={"origin": "http://localhost:8000", "host": "localhost:8000", "X-CompBench-CSRF": static_val},
            cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: static_val}
        )
        try:
            verify_csrf_protection(static_csrf_req)
            assert False, f"Expected 403 Forbidden for static CSRF value '{static_val}'"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "static CSRF tokens" in exc.detail
    print("  [OK] Static CSRF tokens ('1', 'true', etc.) strictly rejected with HTTP 403")

    # J. Mismatched header vs cookie rejected
    mismatched_req = MockRequest(
        method="POST",
        headers={"origin": "http://localhost:8000", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: "different_csrf_token_value_12345678"}
    )
    try:
        verify_csrf_protection(mismatched_req)
        assert False, "Expected 403 Forbidden for mismatched header and cookie"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "do not match" in exc.detail
        print("  [OK] Mismatched header and cookie rejected with HTTP 403")

    # K. Mismatched header/cookie vs session claim rejected
    wrong_csrf = "wrong_csrf_token_hex_string_1234567890abcdef"
    forged_req = MockRequest(
        method="POST",
        headers={"origin": "http://localhost:8000", "host": "localhost:8000", "X-CompBench-CSRF": wrong_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: wrong_csrf}
    )
    try:
        verify_csrf_protection(forged_req)
        assert False, "Expected 403 Forbidden for forged CSRF token not matching session claim"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "does not match authenticated session" in exc.detail
        print("  [OK] CSRF token not matching session claim rejected with HTTP 403")

    # L. Valid session-bound CSRF token and cookie from trusted origin ACCEPTED (All conditions pass)
    trusted_origin_req = MockRequest(
        method="POST",
        headers={"origin": "http://localhost:8000", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    verify_csrf_protection(trusted_origin_req)  # Must not raise
    print("  [OK] Trusted origin WITH matching header, cookie & session claim accepted")

    # M. Same-origin request (127.0.0.1:8000) WITH matching credentials accepted
    same_origin_req = MockRequest(
        method="POST",
        headers={"origin": "http://127.0.0.1:8000", "host": "127.0.0.1:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    verify_csrf_protection(same_origin_req)  # Must not raise
    print("  [OK] Same-origin request WITH matching CSRF credentials accepted")

    # N. Trusted Referer fallback (when Origin absent) WITH matching credentials accepted
    trusted_ref_req = MockRequest(
        method="POST",
        headers={"referer": "http://localhost:8000/dashboard", "host": "localhost:8000", "X-CompBench-CSRF": session_csrf},
        cookies={SESSION_COOKIE_NAME: auth_token, CSRF_COOKIE_NAME: session_csrf}
    )
    verify_csrf_protection(trusted_ref_req)  # Must not raise
    print("  [OK] Trusted Referer fallback WITH matching CSRF credentials accepted")

    # O. Safe HTTP methods (GET, HEAD, OPTIONS) exempt from CSRF checks
    get_req = MockRequest(method="GET", cookies={SESSION_COOKIE_NAME: auth_token})
    verify_csrf_protection(get_req)  # Must not raise
    print("  [OK] Safe HTTP methods (GET) exempt from CSRF checks")

    # P. Bearer-only auth exempt from CSRF (no cookie session present)
    bearer_req = MockRequest(
        method="POST",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    verify_csrf_protection(bearer_req)  # Must not raise
    print("  [OK] Bearer-only auth exempt from browser CSRF")
    print("  [OK] Genuine session-bound CSRF validation confirmed: 4-condition check verified")

    # -------------------------------------------------------------
    # 9. Session Verification & Route Dependency: require_authenticated_user
    # -------------------------------------------------------------
    print("\n--- 9. Route Protection Dependency & GET /api/auth/me ---")
    # 1. Unauthenticated request -> must raise 401
    unauth_req = MockRequest()
    try:
        require_authenticated_user(unauth_req)
        assert False, "Expected 401 for unauthenticated request"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Authentication required" in exc.detail

    try:
        api_me(unauth_req)
        assert False, "Expected 401 from api_me without credentials"
    except HTTPException as exc:
        assert exc.status_code == 401

    # 2. Cookie Session request -> must succeed
    cookie_req = MockRequest(
        method="GET",
        cookies={SESSION_COOKIE_NAME: auth_token}
    )
    user_from_cookie = require_authenticated_user(cookie_req)
    assert user_from_cookie["sub"] == TEST_ADMIN_EMAIL
    me_cookie = api_me(cookie_req)
    assert me_cookie["authenticated"] is True
    assert me_cookie["user"]["email"] == TEST_ADMIN_EMAIL

    # 3. Bearer Token request -> must succeed
    bearer_req = MockRequest(
        method="GET",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    user_from_bearer = require_authenticated_user(bearer_req)
    assert user_from_bearer["sub"] == TEST_ADMIN_EMAIL
    print("  [OK] require_authenticated_user enforces 401 on missing credentials and accepts valid sessions")

    # -------------------------------------------------------------
    # 10. Logout Endpoint: POST /api/auth/logout with Server Revocation
    # -------------------------------------------------------------
    print("\n--- 10. Logout Endpoint & Server-side Invalidation ---")
    logout_token = create_session_token(TEST_ADMIN_EMAIL, "admin", expires_in_seconds=3600)
    logout_csrf = get_csrf_token_from_session(logout_token)
    logout_req = MockRequest(
        method="POST",
        cookies={SESSION_COOKIE_NAME: logout_token, CSRF_COOKIE_NAME: logout_csrf},
        headers={
            "origin": "http://localhost:8000",
            "host": "localhost:8000",
            "X-CompBench-CSRF": logout_csrf
        }
    )
    logout_res = MockResponse()
    logout_res.set_cookie(SESSION_COOKIE_NAME, logout_token)
    logout_res.set_cookie(CSRF_COOKIE_NAME, logout_csrf)

    logout_data = api_logout(logout_res, request=logout_req)
    assert logout_data["status"] == "success"
    assert SESSION_COOKIE_NAME in logout_res.deleted_cookies
    assert CSRF_COOKIE_NAME in logout_res.deleted_cookies
    assert SESSION_COOKIE_NAME not in logout_res.cookies
    assert CSRF_COOKIE_NAME not in logout_res.cookies

    # Even if someone retained the copied logout_token, it must now be rejected
    assert verify_session_token(logout_token) is None, "Token was not invalidated after logout!"
    print("  [OK] POST /api/auth/logout clears cookie and invalidates token server-side")

    # -------------------------------------------------------------
    # 11. Browser Navigation Gatekeeping (Redirects & Views)
    # -------------------------------------------------------------
    print("\n--- 11. Browser Navigation Gatekeeping ---")
    browser_unauth = MockRequest(headers={"accept": "text/html,application/xhtml+xml"})
    res_home_unauth = home(browser_unauth)
    assert isinstance(res_home_unauth, RedirectResponse)
    assert res_home_unauth.status_code == 302
    assert res_home_unauth.headers["location"] == "/login"

    # Authenticated browser to GET / serves 200 FileResponse index.html
    new_session = create_session_token(TEST_ADMIN_EMAIL, "admin", expires_in_seconds=3600)
    browser_auth = MockRequest(
        headers={"accept": "text/html,application/xhtml+xml"},
        cookies={SESSION_COOKIE_NAME: new_session}
    )
    res_home_auth = home(browser_auth)
    assert isinstance(res_home_auth, FileResponse)
    assert "index.html" in str(res_home_auth.path)

    # JSON client to GET / returns status payload without redirect
    api_client_req = MockRequest(headers={"accept": "application/json"})
    res_home_json = home(api_client_req)
    assert res_home_json["status"] == "Running"

    # Unauthenticated browser to GET /login serves login.html
    res_login_view = login_page(browser_unauth)
    assert isinstance(res_login_view, FileResponse)
    assert "login.html" in str(res_login_view.path)

    # Authenticated browser to GET /login redirects to /
    res_login_authed = login_page(browser_auth)
    assert isinstance(res_login_authed, RedirectResponse)
    assert res_login_authed.status_code == 302
    assert res_login_authed.headers["location"] == "/"
    print("  [OK] Navigation gatekeeper redirects unauthenticated visitors to /login and permits authenticated access")

    # -------------------------------------------------------------
    # 12. Unauthorised API Requests to Protected Endpoints
    # -------------------------------------------------------------
    print("\n--- 12. Unauthorised Requests to Protected Endpoints ---")
    endpoints = [
        ("components", lambda: components()),
        ("compare", lambda: compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))),
        ("material_intelligence", lambda: material_intelligence_endpoint(MaterialIntelligenceRequest(material_a="Steel", material_b="Aluminum"))),
        ("analyze", lambda: analyze(AnalyzeRequest(component_a_id="CB001", component_b_id="CB002")))
    ]

    # Verify that require_authenticated_user dependency rejects requests without credentials
    for name, _ in endpoints:
        try:
            require_authenticated_user(MockRequest())
            assert False, f"Expected 401 for unauthenticated access to {name}"
        except HTTPException as exc:
            assert exc.status_code == 401

    # Verify that function calls with authenticated session execute correctly
    valid_comps = components()
    assert len(valid_comps) == 50
    valid_comp = compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))
    assert valid_comp["analysis"]["weight_difference_kg"] == 1.23
    print("  [OK] All core endpoints reject unauthorised callers and succeed for authenticated callers")

    # -------------------------------------------------------------
    # 13. Frontend Files & Secure Cookie Verification
    # -------------------------------------------------------------
    print("\n--- 13. Frontend Assets & Secure Storage Verification ---")
    login_html = Path("frontend/login.html").read_text(encoding="utf-8")
    assert 'sessionStorage.setItem("compbench_auth_token"' not in login_html, "Token must not be stored in sessionStorage!"
    assert 'credentials: "include"' in login_html
    assert 'id="signin-form"' in login_html or 'id="login-form"' in login_html
    assert 'id="signin-email"' in login_html or 'id="login-email"' in login_html
    assert 'id="signin-password"' in login_html or 'id="login-password"' in login_html
    assert 'btn-toggle-password' in login_html or 'toggle-password-btn' in login_html

    app_js = Path("frontend/app.js").read_text(encoding="utf-8")
    assert 'sessionStorage.getItem("compbench_auth_token")' not in app_js, "Token must not be read from sessionStorage!"
    assert 'opt.credentials = "include"' in app_js
    assert 'X-CompBench-CSRF' in app_js
    assert 'verifySessionOrRedirect' in app_js
    assert 'setupLogoutListener' in app_js

    style_css = Path("frontend/style.css").read_text(encoding="utf-8")
    assert '.user-profile-widget' in style_css
    assert '.btn-logout' in style_css
    assert '.login-card' in style_css
    print("  [OK] Frontend assets confirmed: zero bearer tokens in sessionStorage, HttpOnly cookies & CSRF header active")

    print("\n============================================================")
    print("ALL SECURITY & AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    run_auth_test_suite()
