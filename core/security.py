from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from secrets import token_bytes
from typing import Any

import jwt


class SecurityService:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        token_minutes: int = 60,
        password_iterations: int = 210_000,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_minutes = token_minutes
        self.password_iterations = password_iterations

    def hash_password(self, password: str) -> str:
        salt = token_bytes(16)
        digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.password_iterations)
        return f"pbkdf2_sha256${self.password_iterations}${salt.hex()}${digest.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_raw, salt_hex, digest_hex = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_raw)
            digest = pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations)
            return compare_digest(digest.hex(), digest_hex)
        except (ValueError, TypeError):
            return False

    def create_access_token(self, *, subject: str, roles: list[str]) -> str:
        now = datetime.now(UTC)
        claims: dict[str, Any] = {
            "sub": subject,
            "roles": roles,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.token_minutes)).timestamp()),
        }
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        roles = payload.get("roles", [])
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise jwt.InvalidTokenError("roles claim must be a list of strings")
        return payload

