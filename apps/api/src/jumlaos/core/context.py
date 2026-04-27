"""Per-request user + business context, carried via FastAPI Depends."""

from __future__ import annotations

from dataclasses import dataclass

from jumlaos.core.models import Role


@dataclass(slots=True, frozen=True)
class RequestContext:
    """Authoritative context for the current authenticated request."""

    user_id: int
    business_id: int
    role: Role

    def require(self, *roles: Role) -> None:
        from jumlaos.core.errors import Forbidden

        if self.role not in roles:
            raise Forbidden(f"role '{self.role.value}' is not permitted for this action")
