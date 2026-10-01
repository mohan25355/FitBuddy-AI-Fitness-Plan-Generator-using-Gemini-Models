import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


PBKDF2_ITERATIONS = 210000


def hash_admin_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def verify_admin_password(password: str, password_hash: str) -> bool:
    if not password_hash or not password_hash.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, iterations_str, salt_b64, digest_b64 = password_hash.split("$", 3)
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except (ValueError, TypeError, base64.binascii.Error):
        return False
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def session_token(username: str, secret_key: str, expires_hours: int = 12) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = f"{username}:{int(expiry.timestamp())}"
    digest = hashlib.sha256(f"{payload}:{secret_key}".encode("utf-8")).hexdigest()
    return f"{payload}:{digest}"


def verify_session_token(token: str, secret_key: str) -> bool:
    try:
        username, expires_at, digest = token.split(":", 2)
    except ValueError:
        return False
    payload = f"{username}:{expires_at}"
    expected = hashlib.sha256(f"{payload}:{secret_key}".encode("utf-8")).hexdigest()
    if not constant_time_equals(expected, digest):
        return False
    return datetime.now(timezone.utc).timestamp() <= int(expires_at)