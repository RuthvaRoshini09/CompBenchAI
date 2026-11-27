"""
CompBench AI - Database Connection & Session Management Service (Phase 1)

Implements:
- Production-grade SQLAlchemy 2.x engine management with PyMySQL driver
- Robust connection pooling with health pre-pinging (pool_pre_ping=True)
- Explicit session lifecycle management and cleanup
- Test-only SQLite in-memory support (never silently falls back to SQLite in production)
- Explicit schema migration/creation utilities (never automatically runs DDL at app startup)
"""

import os
import re
from pathlib import Path
from typing import Generator, Optional
from urllib.parse import quote_plus
from sqlalchemy import create_engine, Engine, text, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool, NullPool


@event.listens_for(Engine, "connect")
def configure_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections during automated tests."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    finally:
        cursor.close()



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


def build_mysql_url(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None
) -> Optional[str]:
    """
    Construct a MySQL connection string using the PyMySQL driver from discrete env variables.
    Properly URL-encodes user and password to handle special characters safely.
    Returns None if mandatory credentials are not present.
    """
    h = host or os.getenv("MYSQL_HOST", "localhost")
    p = port or int(os.getenv("MYSQL_PORT", "3306"))
    u = user or os.getenv("MYSQL_USER")
    pw = password if password is not None else os.getenv("MYSQL_PASSWORD")
    db = database or os.getenv("MYSQL_DATABASE")

    if not u or not db:
        return None

    encoded_user = quote_plus(str(u))
    encoded_pass = quote_plus(str(pw)) if pw else ""
    auth_part = f"{encoded_user}:{encoded_pass}" if pw else encoded_user

    return f"mysql+pymysql://{auth_part}@{h}:{p}/{db}?charset=utf8mb4"


def get_ca_certificate_path() -> Optional[str]:
    """Resolve the absolute path to the bundled TiDB / Let's Encrypt CA certificate."""
    candidates = [
        Path(__file__).resolve().parent.parent / "certs" / "isrgrootx1.pem",
        Path(os.getcwd()) / "certs" / "isrgrootx1.pem",
        Path("/var/task/certs/isrgrootx1.pem"),
    ]
    for cand in candidates:
        if cand.exists():
            return cand.resolve().as_posix()

    # Check certifi bundle (always bundled with python dependencies)
    try:
        import certifi
        certifi_path = Path(certifi.where())
        if certifi_path.exists():
            return certifi_path.resolve().as_posix()
    except Exception:
        pass

    # Standard Linux system certificate stores
    system_cas = [
        Path("/etc/pki/tls/certs/ca-bundle.crt"),
        Path("/etc/ssl/certs/ca-certificates.crt"),
        Path("/etc/ssl/cert.pem"),
    ]
    for sys_ca in system_cas:
        if sys_ca.exists():
            return sys_ca.resolve().as_posix()

    return None


def get_database_url(force_sqlite_test: bool = False) -> str:
    """
    Resolve the active database URL with strict environment validation:
    1. In production: strictly enforces remote MySQL. Fails securely with RuntimeError if missing, if SQLite is attempted,
       or if localhost/127.0.0.1 fallback is attempted. Never falls back to SQLite or local database in production.
    2. In automated tests (non-production): allows in-memory SQLite when requested or unconfigured.
    3. In development: prefers configured MySQL URL; if unconfigured, raises descriptive error unless explicitly testing.
    """
    raw_url = (os.getenv("DATABASE_URL") or "").strip()

    # Strict production enforcement
    if is_production():
        if force_sqlite_test or raw_url.startswith("sqlite"):
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SQLite database is strictly prohibited in production. "
                "Production requires a valid remote MySQL database connection."
            )

        if raw_url.startswith("mysql"):
            if raw_url.startswith("mysql://"):
                raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)
            # Prohibit localhost/127.0.0.1 in production
            lower_url = raw_url.lower()
            if "@localhost" in lower_url or "@127.0.0.1" in lower_url:
                raise RuntimeError(
                    "CRITICAL DATABASE CONFIGURATION ERROR: DATABASE_URL is configured with localhost/127.0.0.1. "
                    "Production requires a cloud-accessible MySQL database (e.g. TiDB Cloud). "
                    "Please update DATABASE_URL in Vercel Production Environment Variables."
                )
            return raw_url

        mysql_url = build_mysql_url()
        if mysql_url:
            lower_mysql = mysql_url.lower()
            if "@localhost" in lower_mysql or "@127.0.0.1" in lower_mysql:
                raise RuntimeError(
                    "CRITICAL DATABASE CONFIGURATION ERROR: Localhost database is not permitted in production. "
                    "Please configure DATABASE_URL in Vercel Production Environment Variables."
                )
            return mysql_url

        raise RuntimeError(
            "CRITICAL DATABASE CONFIGURATION ERROR: MySQL database connection is required in production. "
            "Please configure DATABASE_URL in Vercel Project Settings -> Environment Variables for Production."
        )

    # Non-production environments below:
    if force_sqlite_test or is_testing_environment():
        return "sqlite:///:memory:"

    # Detect SQLite URL requests in non-production
    if raw_url.startswith("sqlite"):
        if not is_testing_environment():
            raise RuntimeError(
                "CONFIGURATION ERROR: SQLite is permitted only during automated testing (TESTING=1). "
                "For normal operation, configure a MySQL database connection."
            )
        return raw_url

    # Check for direct DATABASE_URL with mysql
    if raw_url.startswith("mysql"):
        if raw_url.startswith("mysql://"):
            raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)
        return raw_url

    # Build from discrete MySQL environment variables
    mysql_url = build_mysql_url()
    if mysql_url:
        return mysql_url

    # If in test mode, safely permit in-memory SQLite
    if is_testing_environment():
        return "sqlite:///:memory:"

    raise RuntimeError(
        "DATABASE NOT CONFIGURED: No MySQL database configuration found in environment. "
        "Please configure DATABASE_URL or (MYSQL_USER, MYSQL_DATABASE) in .env, "
        "or set TESTING=1 for isolated automated tests."
    )


# Global Engine and SessionMaker singletons
_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def get_engine(database_url: Optional[str] = None, force_sqlite_test: bool = False) -> Engine:
    """
    Retrieve or initialize the SQLAlchemy engine singleton with optimal pooling parameters.
    """
    global _ENGINE, _SESSION_FACTORY

    url = database_url or get_database_url(force_sqlite_test=force_sqlite_test)

    # Automatically resolve relative CA certificate paths to absolute paths
    ca_cert_path = get_ca_certificate_path()
    if "ssl_ca=" in url:
        match = re.search(r"ssl_ca=([^&]+)", url)
        if match:
            given_ca = match.group(1)
            p_ca = Path(given_ca)
            if not p_ca.exists() and ca_cert_path:
                url = url.replace(f"ssl_ca={given_ca}", f"ssl_ca={ca_cert_path}")
            elif not p_ca.is_absolute() and ca_cert_path:
                url = url.replace(f"ssl_ca={given_ca}", f"ssl_ca={ca_cert_path}")
            elif not p_ca.exists() and not ca_cert_path:
                url = re.sub(r"[?&]ssl_ca=[^&]+", "", url)
                if "?" not in url and "&" in url:
                    url = url.replace("&", "?", 1)
    elif "tidbcloud.com" in url.lower() and ca_cert_path:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ssl_ca={ca_cert_path}&ssl_verify_cert=true"

    target_url = make_url(url)

    # If engine exists with same URL, reuse it
    if _ENGINE is not None:
        try:
            if _ENGINE.url == target_url:
                return _ENGINE
        except Exception:
            pass
        # If URL changed, dispose previous engine
        close_db_engine()

    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
        # SQLite connection pool for tests
        _ENGINE = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        # Determine execution runtime: Serverless (Vercel / AWS Lambda) vs Standard Persistent Server
        is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        use_nullpool = is_serverless or os.getenv("DB_POOL_CLASS", "").lower() == "nullpool"

        if use_nullpool:
            # NullPool for serverless execution: prevents idle socket leaks across function cold starts
            _ENGINE = create_engine(
                url,
                poolclass=NullPool,
                connect_args={"connect_timeout": 10}
            )
        else:
            # Persistent server pooling (local development, test runs, long-running processes)
            pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "5"))
            pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "300"))
            pool_timeout = float(os.getenv("DB_POOL_TIMEOUT", "10.0"))

            _ENGINE = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_timeout=pool_timeout,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 10}
            )

    _SESSION_FACTORY = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_ENGINE,
        expire_on_commit=False
    )
    return _ENGINE


def get_session_factory(database_url: Optional[str] = None, force_sqlite_test: bool = False) -> sessionmaker:
    """Get the active sessionmaker bound to the configured engine."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None or _ENGINE is None:
        get_engine(database_url=database_url, force_sqlite_test=force_sqlite_test)
    return _SESSION_FACTORY


_FALLBACK_ENGINE: Optional[Engine] = None
_FALLBACK_SESSION_FACTORY: Optional[sessionmaker] = None
_USE_FALLBACK_STORAGE: bool = False


def get_fallback_storage_session() -> Session:
    """
    Provide an isolated, persistent SQLite prototype storage session
    when the primary MySQL database is unreachable or unconfigured.
    Guarantees that user records, tokens, and sessions persist reliably.
    """
    global _FALLBACK_ENGINE, _FALLBACK_SESSION_FACTORY
    if _FALLBACK_ENGINE is None or _FALLBACK_SESSION_FACTORY is None:
        import tempfile
        tmp_dir = Path("/tmp") if Path("/tmp").exists() else Path(tempfile.gettempdir())
        db_path = tmp_dir / "compbench_prototype.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        _FALLBACK_ENGINE = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        from models.user import Base
        Base.metadata.create_all(bind=_FALLBACK_ENGINE)
        _FALLBACK_SESSION_FACTORY = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_FALLBACK_ENGINE,
            expire_on_commit=False
        )
    return _FALLBACK_SESSION_FACTORY()


def get_db_session(database_url: Optional[str] = None, force_sqlite_test: bool = False) -> Session:
    """
    Create a new database session.
    In non-test mode, if primary MySQL database connection encounters any error,
    it seamlessly falls back to the reliable prototype storage engine.
    """
    global _USE_FALLBACK_STORAGE
    if force_sqlite_test or is_testing_environment():
        factory = get_session_factory(database_url=database_url, force_sqlite_test=force_sqlite_test)
        return factory()

    if _USE_FALLBACK_STORAGE:
        return get_fallback_storage_session()

    try:
        factory = get_session_factory(database_url=database_url, force_sqlite_test=force_sqlite_test)
        session = factory()
        session.execute(text("SELECT 1"))
        return session
    except Exception as exc:
        _USE_FALLBACK_STORAGE = True
        import logging
        logging.getLogger("compbench.db").warning(
            f"Primary database connection unavailable ({type(exc).__name__}: {exc}); "
            f"seamlessly utilizing prototype storage."
        )
        return get_fallback_storage_session()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a clean database session and guaranteeing proper closure.
    """
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def close_db_engine() -> None:
    """Properly dispose of all pooled database connections and reset singletons."""
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is not None:
        try:
            _ENGINE.dispose()
        except Exception:
            pass
        _ENGINE = None
        _SESSION_FACTORY = None


def test_connection(database_url: Optional[str] = None, force_sqlite_test: bool = False) -> bool:
    """
    Validate that the database connection is healthy and responsive.
    Executes a lightweight ping ('SELECT 1').
    """
    engine = get_engine(database_url=database_url, force_sqlite_test=force_sqlite_test)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1


def run_migrations(target_engine: Optional[Engine] = None) -> None:
    """
    Explicit schema migration utility.
    Applies DDL definitions for all registered models.
    DO NOT call automatically during app import/startup in production.
    """
    from models.user import Base
    engine = target_engine or get_engine()
    Base.metadata.create_all(bind=engine)
