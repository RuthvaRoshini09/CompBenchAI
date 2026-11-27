"""
CompBench AI - Multi-User Authentication Database Models (Phase 1)

Defines:
- User: Multi-user registry with full_name, email, password_hash, role ('admin' or 'user'), is_verified
- EmailVerificationToken: High-entropy SHA-256 hashed verification tokens for Resend email workflow
- PasswordResetToken: High-entropy SHA-256 hashed password reset tokens
- RevokedToken: Distributed server-side session revocation blacklist (jti, expiration)
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)


def get_utc_now() -> datetime:
    """Return timezone-naive UTC timestamp for standard SQL DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base declarative class for all CompBench AI database models."""
    pass


# Primary key integer type that is BIGINT on MySQL and INTEGER on SQLite for autoincrement compatibility
PK_BIGINT = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    """
    User entity representing registered CompBench AI users and administrators.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")  # 'admin' or 'user'
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )

    # Relationships to verification and reset tokens (with full cascade delete)
    verification_tokens: Mapped[List["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}' is_verified={self.is_verified}>"


class EmailVerificationToken(Base):
    """
    Stores single-use SHA-256 hashed verification tokens associated with user accounts.
    Raw tokens are sent strictly to the user via Resend API and never stored in plaintext.
    """
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        PK_BIGINT,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="verification_tokens")

    __table_args__ = (
        Index("idx_evt_token_hash", "token_hash"),
        Index("idx_evt_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken id={self.id} user_id={self.user_id} used={self.used_at is not None}>"


class PasswordResetToken(Base):
    """
    Stores single-use SHA-256 hashed password reset tokens with strict expiration.
    """
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        PK_BIGINT,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index("idx_prt_token_hash", "token_hash"),
        Index("idx_prt_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} used={self.used_at is not None}>"


class RevokedToken(Base):
    """
    Distributed session token revocation blacklist for tracking revoked JWT jti identifiers.
    Enables instant session invalidation across multi-worker deployments.
    """
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("idx_revoked_jti", "jti"),
        Index("idx_revoked_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<RevokedToken id={self.id} jti='{self.jti}' expires_at='{self.expires_at}'>"

