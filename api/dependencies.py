from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.security import SecurityService
from domain.models import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: list[str]

    def has_role(self, role: Role) -> bool:
        return role.value in self.roles or Role.ADMIN.value in self.roles


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_security_service(request: Request) -> SecurityService:
    return request.app.state.security


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_principal(
    token: str = Depends(oauth2_scheme),
    security_service: SecurityService = Depends(get_security_service),
) -> Principal:
    try:
        payload = security_service.decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return Principal(subject=str(payload["sub"]), roles=list(payload.get("roles", [])))


def require_role(role: Role) -> Callable[[Principal], Principal]:
    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_role(role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return principal

    return dependency

