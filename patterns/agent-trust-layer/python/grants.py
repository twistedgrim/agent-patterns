"""
Time-bound grant management for agent permissions.

Grants are scoped, time-limited permissions that can be revoked.
This implements least-privilege with automatic expiration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from fnmatch import fnmatch
import uuid


class GrantStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Grant:
    """Immutable permission grant with expiration."""

    grant_id: str
    agent_id: str
    scope: str  # e.g., "file:read:/workspace/*"
    issued_at: datetime
    expires_at: datetime
    issuer: str
    revoked: bool = False
    metadata: tuple[tuple[str, str], ...] = ()

    def status(self) -> GrantStatus:
        """Current status of the grant."""
        if self.revoked:
            return GrantStatus.REVOKED
        if datetime.utcnow() > self.expires_at:
            return GrantStatus.EXPIRED
        return GrantStatus.ACTIVE

    def is_valid(self) -> bool:
        """Check if grant is currently valid."""
        return self.status() == GrantStatus.ACTIVE

    def matches_scope(self, requested_scope: str) -> bool:
        """Check if this grant covers the requested scope."""
        # Scope format: "action:resource" e.g., "file:read:/workspace/foo.py"
        grant_parts = self.scope.split(":", 2)
        request_parts = requested_scope.split(":", 2)

        if len(grant_parts) < 2 or len(request_parts) < 2:
            return False

        # Check action matches
        if grant_parts[0] != request_parts[0] and grant_parts[0] != "*":
            return False

        # Check sub-action matches (read, write, etc.)
        if grant_parts[1] != request_parts[1] and grant_parts[1] != "*":
            return False

        # Check resource pattern (glob matching)
        if len(grant_parts) > 2 and len(request_parts) > 2:
            return fnmatch(request_parts[2], grant_parts[2])

        return True


@dataclass
class GrantPolicy:
    """Policy constraints for grant issuance."""

    max_ttl_seconds: int = 3600
    require_confirmation: bool = False
    audit_level: str = "NORMAL"


class GrantStore:
    """Storage and management for grants."""

    def __init__(self) -> None:
        self._grants: dict[str, Grant] = {}
        self._by_agent: dict[str, list[str]] = {}
        self._policies: dict[str, GrantPolicy] = {}

    def set_policy(self, scope_prefix: str, policy: GrantPolicy) -> None:
        """Set policy for a scope prefix."""
        self._policies[scope_prefix] = policy

    def get_policy(self, scope: str) -> GrantPolicy:
        """Get applicable policy for a scope."""
        # Find most specific matching policy
        best_match = ""
        for prefix in self._policies:
            if scope.startswith(prefix) and len(prefix) > len(best_match):
                best_match = prefix

        return self._policies.get(best_match, GrantPolicy())

    def issue(
        self,
        agent_id: str,
        scope: str,
        ttl_seconds: int,
        issuer: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> Grant:
        """Issue a new grant with policy enforcement."""
        policy = self.get_policy(scope)

        # Enforce max TTL
        effective_ttl = min(ttl_seconds, policy.max_ttl_seconds)

        now = datetime.utcnow()
        grant = Grant(
            grant_id=str(uuid.uuid4()),
            agent_id=agent_id,
            scope=scope,
            issued_at=now,
            expires_at=now + timedelta(seconds=effective_ttl),
            issuer=issuer,
            metadata=tuple((metadata or {}).items()),
        )

        self._grants[grant.grant_id] = grant

        if agent_id not in self._by_agent:
            self._by_agent[agent_id] = []
        self._by_agent[agent_id].append(grant.grant_id)

        return grant

    def check(self, agent_id: str, requested_scope: str) -> Optional[Grant]:
        """Check if agent has a valid grant for the requested scope."""
        grant_ids = self._by_agent.get(agent_id, [])

        for grant_id in grant_ids:
            grant = self._grants.get(grant_id)
            if grant and grant.is_valid() and grant.matches_scope(requested_scope):
                return grant

        return None

    def revoke(self, grant_id: str) -> bool:
        """Revoke a grant by ID."""
        grant = self._grants.get(grant_id)
        if not grant:
            return False

        # Create revoked version (grants are immutable)
        revoked_grant = Grant(
            grant_id=grant.grant_id,
            agent_id=grant.agent_id,
            scope=grant.scope,
            issued_at=grant.issued_at,
            expires_at=grant.expires_at,
            issuer=grant.issuer,
            revoked=True,
            metadata=grant.metadata,
        )
        self._grants[grant_id] = revoked_grant
        return True

    def revoke_all_for_agent(self, agent_id: str) -> int:
        """Revoke all grants for an agent."""
        grant_ids = self._by_agent.get(agent_id, [])
        count = 0
        for grant_id in grant_ids:
            if self.revoke(grant_id):
                count += 1
        return count

    def list_grants(
        self, agent_id: Optional[str] = None, include_expired: bool = False
    ) -> list[Grant]:
        """List grants, optionally filtered by agent."""
        grants = []

        if agent_id:
            grant_ids = self._by_agent.get(agent_id, [])
            grants = [self._grants[gid] for gid in grant_ids if gid in self._grants]
        else:
            grants = list(self._grants.values())

        if not include_expired:
            grants = [g for g in grants if g.is_valid()]

        return grants

    def cleanup_expired(self) -> int:
        """Remove expired grants from storage."""
        expired = [gid for gid, g in self._grants.items() if not g.is_valid()]

        for grant_id in expired:
            grant = self._grants.pop(grant_id)
            if grant.agent_id in self._by_agent:
                self._by_agent[grant.agent_id] = [
                    gid
                    for gid in self._by_agent[grant.agent_id]
                    if gid != grant_id
                ]

        return len(expired)


# Example usage
if __name__ == "__main__":
    store = GrantStore()

    # Set policies
    store.set_policy("file:read", GrantPolicy(max_ttl_seconds=86400))
    store.set_policy("file:write", GrantPolicy(max_ttl_seconds=3600))
    store.set_policy(
        "shell:execute",
        GrantPolicy(max_ttl_seconds=300, require_confirmation=True),
    )

    # Issue grants
    read_grant = store.issue(
        agent_id="code-assistant-01",
        scope="file:read:/workspace/*",
        ttl_seconds=7200,
        issuer="admin",
    )
    print(f"Issued read grant: {read_grant.grant_id[:8]}...")
    print(f"  Scope: {read_grant.scope}")
    print(f"  Expires: {read_grant.expires_at}")

    write_grant = store.issue(
        agent_id="code-assistant-01",
        scope="file:write:/workspace/src/*",
        ttl_seconds=1800,
        issuer="admin",
    )
    print(f"Issued write grant: {write_grant.grant_id[:8]}...")

    # Check permissions
    can_read = store.check("code-assistant-01", "file:read:/workspace/main.py")
    print(f"\nCan read /workspace/main.py: {can_read is not None}")

    can_write = store.check("code-assistant-01", "file:write:/workspace/src/app.py")
    print(f"Can write /workspace/src/app.py: {can_write is not None}")

    can_delete = store.check("code-assistant-01", "file:delete:/workspace/main.py")
    print(f"Can delete /workspace/main.py: {can_delete is not None}")

    # Revoke a grant
    store.revoke(write_grant.grant_id)
    can_write_after = store.check(
        "code-assistant-01", "file:write:/workspace/src/app.py"
    )
    print(f"\nAfter revocation, can write: {can_write_after is not None}")
