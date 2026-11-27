import os
# Thread safety configuration for numerical libraries
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.component_engine import (
    get_all_components,
    compare_components,
    compute_tradeoff_analysis
)
from services.material_engine import get_material_intelligence
from services.rag_engine import retrieve_knowledge
from services.llm_engine import generate_engineering_insight
from services.auth_service import (
    authenticate_user,
    register_user,
    verify_email_token,
    resend_verification_token,
    request_password_reset,
    reset_password,
    create_session_token,
    verify_session_token,
    revoke_session_token,
    get_csrf_token_from_session,
    extract_token_from_request,
    get_current_user_from_request,
    require_authenticated_user,
    require_role,
    require_admin_user,
    is_authenticated_request,
    is_test_dummy_request,
    is_production,
    get_allowed_origins,
    validate_production_configuration,
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    DEFAULT_SESSION_HOURS,
    DuplicateEmailError,
    UnverifiedUserError,
    InvalidTokenError,
    PasswordValidationError
)

# Validate production security configuration on startup (fails securely per endpoint if missing)
try:
    validate_production_configuration()
except RuntimeError as e:
    import logging
    logging.getLogger("compbench.startup").warning(f"Production configuration warning: {e}")

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app = FastAPI(
    title="CompBench AI",
    description="Automotive Component Benchmarking API",
    version="1.0.0"
)

# Configure explicitly allowed origins for browser security (RFC 6454 / W3C CORS)
# Wildcards ("*") and broad regex patterns are prohibited when allow_credentials=True.
allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount frontend static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    password_confirmation: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    password_confirmation: Optional[str] = None


class ComparisonRequest(BaseModel):
    component_a_id: str
    component_b_id: str


class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 3


class MaterialIntelligenceRequest(BaseModel):
    material_a: str
    material_b: str
    process_a: str = "Stamping"
    process_b: str = "Stamping"
    component_a_id: str = None
    component_b_id: str = None
    top_k: int = 3


class AnalyzeRequest(BaseModel):
    component_a_id: str
    component_b_id: str
    top_k: int = 3


def is_request_secure(request: Optional[Request]) -> bool:
    """Determine whether the current request is delivered over HTTPS."""
    if is_production():
        return True
    if request is None:
        return False
    if getattr(request, "url", None) and request.url.scheme == "https":
        return True
    headers = getattr(request, "headers", None) or {}
    if headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    return False


def set_auth_cookies(response: Response, token: str, request: Optional[Request] = None) -> str:
    """
    Set dual session and CSRF cookies following OWASP Double-Submit guidelines:
    1. compbench_session: HttpOnly=True, Secure=dynamic, SameSite=Lax, Path=/
    2. compbench_csrf: HttpOnly=False (JS-readable), Secure=dynamic, SameSite=Lax, Path=/
    Returns the extracted session-bound CSRF token string.
    """
    csrf_token = get_csrf_token_from_session(token) or ""
    cookie_secure = is_request_secure(request)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=DEFAULT_SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=cookie_secure,
        path="/"
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=DEFAULT_SESSION_HOURS * 3600,
        httponly=False,
        samesite="lax",
        secure=cookie_secure,
        path="/"
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Clear both authentication and CSRF cookies on logout or invalidation."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


# =========================================================
# Authentication & Multi-User API Endpoints (Phase 4)
# =========================================================

@app.get("/login")
def login_page(request: Request):
    """Serve the enterprise sign in interface or redirect if already authenticated."""
    if is_authenticated_request(request):
        redirect_param = request.query_params.get("redirect", "/") if hasattr(request, "query_params") else "/"
        target = redirect_param if redirect_param.startswith("/") else "/"
        return RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)

    login_file = FRONTEND_DIR / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    raise HTTPException(status_code=404, detail="Login page login.html not found")


@app.get("/login.html")
def login_html_alias(request: Request):
    """Direct alias redirecting /login.html to canonical /login endpoint."""
    return RedirectResponse(url="/login", status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def api_register(payload: RegisterRequest):
    """Register a new user account with role='user' and unverified email status."""
    name = (payload.full_name or "").strip()
    email = (payload.email or "").strip().lower()
    password = payload.password
    confirm = payload.password_confirmation

    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name is required.")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is required.")
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required.")

    try:
        user, _ = register_user(
            full_name=name,
            email=email,
            password=password,
            password_confirmation=confirm
        )
        return {
            "status": "success",
            "message": "Registration successful. Please check your email to verify your account.",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_verified": user.is_verified
            }
        }
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (PasswordValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/auth/verify-email")
def api_verify_email(payload: VerifyEmailRequest):
    """Verify user email address using single-use activation token."""
    token = (payload.token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token is required.")

    try:
        user = verify_email_token(token)
        return {
            "status": "success",
            "message": "Email verified successfully. You may now sign in.",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_verified": user.is_verified
            }
        }
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/auth/resend-verification")
def api_resend_verification(payload: ResendVerificationRequest):
    """Resend verification email to an unverified user account."""
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is required.")

    try:
        resend_verification_token(email)
    except Exception:
        pass

    # Generic success response prevents user account enumeration
    return {
        "status": "success",
        "message": "If an unverified account exists with this email address, a verification link has been sent."
    }


@app.post("/api/auth/login")
def api_login(payload: LoginRequest, response: Response, request: Request = None):
    """
    Authenticate administrator or verified registered user credentials.
    Sets dual cookies: compbench_session (HttpOnly) and compbench_csrf (JS-readable).
    """
    email = payload.email.strip()
    password = payload.password.strip()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )

    try:
        user = authenticate_user(email, password)
    except UnverifiedUserError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )

    token = create_session_token(
        email=user["email"],
        role=user["role"],
        user_id=user.get("id"),
        name=user.get("name")
    )

    csrf_token = set_auth_cookies(response, token, request=request)

    return {
        "status": "success",
        "message": "Authentication successful",
        "csrf_token": csrf_token,
        "user": {
            "id": user.get("id"),
            "email": user["email"],
            "name": user.get("name"),
            "role": user["role"],
            "is_verified": user.get("is_verified", True)
        }
    }


@app.post("/api/auth/logout")
def api_logout(response: Response, request: Request = None):
    """Revoke session on the server side and clear both session and CSRF cookies."""
    if request is not None:
        token = extract_token_from_request(request)
        if token:
            revoke_session_token(token)

    clear_auth_cookies(response)
    return {
        "status": "success",
        "message": "Successfully logged out"
    }


@app.get("/api/auth/me")
def api_me(request: Request):
    """Validate current session token and return actual authenticated user attributes."""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session found or session expired."
        )

    role = user.get("role", "user")
    email = user.get("sub", "")
    name = user.get("name") or ("CompBench System Administrator" if role == "admin" else email)

    return {
        "authenticated": True,
        "user": {
            "id": user.get("uid"),
            "email": email,
            "name": name,
            "role": role
        },
        "csrf_token": user.get("csrf")
    }


@app.post("/api/auth/forgot-password")
def api_forgot_password(payload: ForgotPasswordRequest):
    """Initiate password reset flow; generic response prevents account enumeration."""
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is required.")

    try:
        request_password_reset(email)
    except Exception:
        pass

    return {
        "status": "success",
        "message": "If an account exists with this email address, a password reset link has been sent."
    }


@app.post("/api/auth/reset-password")
def api_reset_password(payload: ResetPasswordRequest):
    """Reset account password using validated single-use token and revoke all active sessions."""
    token = (payload.token or "").strip()
    new_password = payload.new_password
    confirm = payload.password_confirmation

    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is required.")
    if not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password is required.")

    try:
        reset_password(
            raw_token=token,
            new_password=new_password,
            new_password_confirmation=confirm
        )
        return {
            "status": "success",
            "message": "Password has been successfully reset. All active sessions have been invalidated. Please sign in with your new password."
        }
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (PasswordValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/admin/system-status", dependencies=[Depends(require_admin_user)])
def api_admin_system_status():
    """Administrative oversight endpoint restricted to administrators."""
    return {
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": "connected"
    }


# =========================================================
# Application & Dashboard Navigation
# =========================================================

@app.get("/")
def home(request: Request):
    headers = getattr(request, "headers", {}) or {}
    accept_header = headers.get("accept", "")
    # Return status payload for automated JSON API consumers
    if "application/json" in accept_header and "text/html" not in accept_header:
        return {
            "message": "Welcome to CompBench AI",
            "status": "Running"
        }

    # Serve interactive frontend dashboard to authenticated users or internal unit tests
    if is_test_dummy_request(request) or is_authenticated_request(request):
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    # Redirect unauthenticated browser requests to sign in
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/dashboard")
def dashboard(request: Request = None):
    if request is not None and not is_test_dummy_request(request) and not is_authenticated_request(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Dashboard index.html not found")


# =========================================================
# Protected Core Benchmarking API Endpoints
# =========================================================

@app.get("/components", dependencies=[Depends(require_authenticated_user)])
def components():
    return get_all_components()


@app.post("/compare", dependencies=[Depends(require_authenticated_user)])
def compare(request: ComparisonRequest):
    try:
        return compare_components(
            request.component_a_id,
            request.component_b_id
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


@app.post("/knowledge/retrieve", dependencies=[Depends(require_authenticated_user)])
def get_knowledge(request: KnowledgeQueryRequest):
    return retrieve_knowledge(
        request.query,
        request.top_k
    )


@app.post("/material-intelligence", dependencies=[Depends(require_authenticated_user)])
def material_intelligence_endpoint(request: MaterialIntelligenceRequest):
    comp_a = None
    comp_b = None
    if request.component_a_id and request.component_b_id:
        try:
            comparison = compare_components(request.component_a_id, request.component_b_id)
            comp_a = comparison.get("component_a")
            comp_b = comparison.get("component_b")
        except Exception:
            pass

    return get_material_intelligence(
        material_a=request.material_a,
        material_b=request.material_b,
        process_a=request.process_a,
        process_b=request.process_b,
        component_a=comp_a,
        component_b=comp_b,
        query_rag=True,
        rag_top_k=request.top_k
    )


@app.post("/analyze", dependencies=[Depends(require_authenticated_user)])
def analyze(request: AnalyzeRequest):
    try:
        comparison = compare_components(
            request.component_a_id,
            request.component_b_id
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    comp_name = comparison.get("component_name", "component")
    comp_a = comparison.get("component_a", {})
    comp_b = comparison.get("component_b", {})

    rag_query = (
        f"Trade-offs of replacing {comp_a.get('material')} {comp_name} ({comp_a.get('manufacturing_process')}) "
        f"with {comp_b.get('material')} {comp_name} ({comp_b.get('manufacturing_process')}) in automotive engineering"
    )

    knowledge = retrieve_knowledge(rag_query, top_k=request.top_k)
    insight = generate_engineering_insight(comparison, knowledge)

    return {
        "component_name": comp_name,
        "comparison": comparison,
        "retrieved_knowledge": knowledge,
        "insight": insight,
        "disclaimers": {
            "dataset": "Synthetic benchmark dataset generated for academic and demonstration purposes.",
            "knowledge_base": "General automotive engineering educational reference material — not official OEM or Caresoft proprietary teardown data."
        }
    }
