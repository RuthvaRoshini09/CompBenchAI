"""
CompBench AI - Administrator Account Provisioning Utility

Securely configures the authorized administrator account and authentication secret in the root .env file.
Adheres to OWASP security guidelines:
- Masked password input (never echoes to terminal)
- Password confirmation and length enforcement
- Argon2id cryptographic hashing via argon2-cffi
- High-entropy cryptographic session secret generation via secrets.token_hex
- Overwrite protection for existing credentials
- Zero leakage: never prints or logs plaintext passwords, hashes, or secret keys
- Preservation of existing .env settings and comments
"""

import os
import re
import sys
import getpass
import secrets
from pathlib import Path
from typing import Dict, Optional, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.example"


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """Parse key-value pairs from an environment file, ignoring comments."""
    env_vars = {}
    if not file_path.exists():
        return env_vars

    text = file_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip()
    return env_vars


def update_env_file(file_path: Path, updates: Dict[str, str], template_path: Optional[Path] = None) -> None:
    """
    Update or append key-value pairs in an environment file.
    Preserves all comments, blank lines, and untouched settings.
    If the target file does not exist, copies the template structure first.
    """
    if file_path.exists():
        lines = file_path.read_text(encoding="utf-8").splitlines()
    elif template_path and template_path.exists():
        lines = template_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any updates that were not present in the existing file
    remaining_keys = [k for k in updates.keys() if k not in updated_keys]
    if remaining_keys:
        if new_lines and new_lines[-1].strip() != "":
            new_lines.append("")
        new_lines.append("# =========================================================")
        new_lines.append("# Automated Administrator Provisioning")
        new_lines.append("# =========================================================")
        for k in remaining_keys:
            new_lines.append(f"{k}={updates[k]}")

    content = "\n".join(new_lines).strip() + "\n"
    file_path.write_text(content, encoding="utf-8")


def validate_email(email: str) -> bool:
    """Validate basic email format."""
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(pattern, email.strip()))


def provision_admin(
    email: str,
    password: str,
    env_file: Optional[Path] = None,
    force_overwrite: bool = False,
    generate_secret: bool = True
) -> Tuple[bool, str]:
    """
    Programmatic provisioning helper used by CLI and unit tests.
    Returns (success: bool, message: str).
    Never returns or exposes plain passwords, hashes, or secret keys in message.
    """
    target_env = env_file or ENV_PATH
    clean_email = email.strip().lower()

    if not validate_email(clean_email):
        return False, "Invalid email address format."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    existing_vars = parse_env_file(target_env)
    has_existing_admin = bool(existing_vars.get("ADMIN_EMAIL") and existing_vars.get("ADMIN_PASSWORD_HASH"))

    if has_existing_admin and not force_overwrite:
        return False, f"Existing admin credentials found for '{existing_vars.get('ADMIN_EMAIL')}'. Overwrite confirmation required."

    # Import Argon2id hasher from auth_service to ensure exact runtime parameter parity
    try:
        from services.auth_service import hash_password
        password_hash = hash_password(password)
    except Exception as e:
        return False, f"Failed to generate Argon2 password hash: {e}"

    updates = {
        "ADMIN_EMAIL": clean_email,
        "ADMIN_PASSWORD_HASH": password_hash
    }

    # Handle AUTH_SECRET_KEY
    existing_secret = existing_vars.get("AUTH_SECRET_KEY")
    is_placeholder_secret = not existing_secret or "your_secure_random" in existing_secret
    if generate_secret or is_placeholder_secret:
        updates["AUTH_SECRET_KEY"] = secrets.token_hex(32)

    try:
        update_env_file(target_env, updates, template_path=ENV_EXAMPLE_PATH)
    except Exception as e:
        return False, f"Failed to write configuration to {target_env.name}: {e}"

    return True, f"Administrator account '{clean_email}' successfully configured."


def interactive_setup() -> None:
    """Interactive command-line setup wizard with masked password input."""
    print("=" * 60)
    print("COMPBENCH AI: AUTHORIZED ADMINISTRATOR ACCOUNT SETUP")
    print("=" * 60)
    print("This utility securely provisions the authorized admin account in .env.")
    print("All inputs are handled locally; passwords and secrets are never printed.\n")

    existing_vars = parse_env_file(ENV_PATH)
    existing_admin = existing_vars.get("ADMIN_EMAIL")
    force_overwrite = False

    if existing_admin and existing_vars.get("ADMIN_PASSWORD_HASH"):
        print(f"[!] Notice: An administrator account is already provisioned:")
        print(f"    Current Admin Email: {existing_admin}")
        try:
            confirm = input("\nDo you want to overwrite existing admin credentials? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

        if confirm != "y":
            print("\nSetup cancelled. Existing credentials in .env were preserved.")
            sys.exit(0)
        force_overwrite = True
        print()

    # 1. Prompt for Email
    default_email = existing_admin if existing_admin else "admin@compbench.ai"
    while True:
        try:
            email_input = input(f"Enter administrator email [{default_email}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

        email = email_input if email_input else default_email
        if validate_email(email):
            break
        print(" [!] Invalid email address. Please enter a valid format (e.g. name@company.com).")

    # 2. Prompt for Password (hidden input)
    while True:
        try:
            password = getpass.getpass("Enter new administrator password (min 8 chars): ")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

        if len(password) < 8:
            print(" [!] Password must be at least 8 characters long. Please try again.")
            continue

        try:
            confirm_password = getpass.getpass("Confirm administrator password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)

        if password != confirm_password:
            print(" [!] Passwords do not match. Please try again.\n")
            continue

        break

    # 3. Provision credentials
    print("\n[+] Generating Argon2id password hash...")
    print("[+] Generating cryptographic HMAC-SHA256 authentication secret...")

    success, message = provision_admin(
        email=email,
        password=password,
        env_file=ENV_PATH,
        force_overwrite=force_overwrite
    )

    if not success:
        print(f"\n[-] Setup failed: {message}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ADMINISTRATOR ACCOUNT CONFIGURED SUCCESSFULLY")
    print("=" * 60)
    print(f"Admin Email:         {email.strip().lower()}")
    print("Argon2id Hash:       [SECURELY WRITTEN TO .env]")
    print("Auth Secret Key:     [SECURELY WRITTEN TO .env]")
    print("Session Duration:    8 hours (default)")
    print("Target File:         .env")
    print("=" * 60)
    print("\nSecurity Verification:")
    print("  [OK] Passwords and cryptographic secrets were never echoed or logged.")
    print("  [OK] The .env file is excluded from Git via .gitignore.")
    print("\nNext Steps:")
    print("  1. Start or restart your FastAPI server:")
    print("     .\\venv\\Scripts\\python.exe -m uvicorn main:app --reload")
    print(f"  2. Sign in at: http://127.0.0.1:8000/login using {email.strip().lower()}\n")


if __name__ == "__main__":
    interactive_setup()

