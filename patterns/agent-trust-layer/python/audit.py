"""
Append-only audit log for agent actions.

Records all agent actions with cryptographic attribution
for forensics and compliance.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Iterator
import hashlib
import json


class ActionType(Enum):
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    SHELL_EXECUTE = "shell:execute"
    API_CALL = "api:call"
    GRANT_ISSUED = "grant:issued"
    GRANT_REVOKED = "grant:revoked"
    IDENTITY_CREATED = "identity:created"
    IDENTITY_REVOKED = "identity:revoked"


class AuditLevel(Enum):
    MINIMAL = "minimal"  # Action type and result only
    NORMAL = "normal"  # Include resource and agent
    VERBOSE = "verbose"  # Include full context and arguments


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry with chain integrity."""

    entry_id: str
    timestamp: datetime
    agent_id: str
    action_type: ActionType
    resource: str
    result: str  # "success", "denied", "error"
    signature: bytes
    previous_hash: bytes
    grant_id: Optional[str] = None
    context: tuple[tuple[str, str], ...] = ()

    def compute_hash(self) -> bytes:
        """Compute hash of this entry for chain integrity."""
        data = f"{self.entry_id}:{self.timestamp.isoformat()}:{self.agent_id}"
        data += f":{self.action_type.value}:{self.resource}:{self.result}"
        data += f":{self.previous_hash.hex()}"
        return hashlib.sha256(data.encode()).digest()


class AuditLog:
    """Append-only audit log with chain integrity."""

    def __init__(self, audit_level: AuditLevel = AuditLevel.NORMAL) -> None:
        self._entries: list[AuditEntry] = []
        self._audit_level = audit_level
        self._entry_counter = 0
        # Genesis hash for first entry
        self._last_hash = hashlib.sha256(b"genesis").digest()

    def record(
        self,
        agent_id: str,
        action_type: ActionType,
        resource: str,
        result: str,
        signature: bytes,
        grant_id: Optional[str] = None,
        context: Optional[dict[str, str]] = None,
    ) -> AuditEntry:
        """Record an action in the audit log."""
        self._entry_counter += 1

        # Filter context based on audit level
        filtered_context: dict[str, str] = {}
        if context and self._audit_level == AuditLevel.VERBOSE:
            filtered_context = context
        elif context and self._audit_level == AuditLevel.NORMAL:
            # Include only non-sensitive keys
            safe_keys = {"user", "session", "request_id"}
            filtered_context = {k: v for k, v in context.items() if k in safe_keys}

        entry = AuditEntry(
            entry_id=f"audit-{self._entry_counter:08d}",
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            action_type=action_type,
            resource=resource,
            result=result,
            signature=signature,
            previous_hash=self._last_hash,
            grant_id=grant_id,
            context=tuple(filtered_context.items()),
        )

        self._entries.append(entry)
        self._last_hash = entry.compute_hash()

        return entry

    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """Verify integrity of the audit chain."""
        if not self._entries:
            return True, None

        expected_hash = hashlib.sha256(b"genesis").digest()

        for i, entry in enumerate(self._entries):
            # Check previous hash matches
            if entry.previous_hash != expected_hash:
                return False, f"Chain broken at entry {i}: {entry.entry_id}"

            expected_hash = entry.compute_hash()

        return True, None

    def query(
        self,
        agent_id: Optional[str] = None,
        action_type: Optional[ActionType] = None,
        resource_prefix: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with filters."""
        results = []

        for entry in reversed(self._entries):
            if len(results) >= limit:
                break

            if agent_id and entry.agent_id != agent_id:
                continue
            if action_type and entry.action_type != action_type:
                continue
            if resource_prefix and not entry.resource.startswith(resource_prefix):
                continue
            if since and entry.timestamp < since:
                continue
            if until and entry.timestamp > until:
                continue

            results.append(entry)

        return list(reversed(results))

    def get_agent_activity(self, agent_id: str) -> dict[str, int]:
        """Get activity summary for an agent."""
        activity: dict[str, int] = {}

        for entry in self._entries:
            if entry.agent_id == agent_id:
                key = f"{entry.action_type.value}:{entry.result}"
                activity[key] = activity.get(key, 0) + 1

        return activity

    def export_json(self, entries: Optional[list[AuditEntry]] = None) -> str:
        """Export entries as JSON for external analysis."""
        target = entries if entries is not None else self._entries

        data = [
            {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp.isoformat(),
                "agent_id": e.agent_id,
                "action_type": e.action_type.value,
                "resource": e.resource,
                "result": e.result,
                "grant_id": e.grant_id,
                "context": dict(e.context),
            }
            for e in target
        ]

        return json.dumps(data, indent=2)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[AuditEntry]:
        return iter(self._entries)


# Example usage
if __name__ == "__main__":
    log = AuditLog(audit_level=AuditLevel.VERBOSE)

    # Simulate agent actions
    dummy_signature = b"agent-signature-placeholder"

    # Record file read
    log.record(
        agent_id="code-assistant-01",
        action_type=ActionType.FILE_READ,
        resource="/workspace/main.py",
        result="success",
        signature=dummy_signature,
        grant_id="grant-001",
        context={"user": "developer", "session": "sess-123"},
    )

    # Record file write
    log.record(
        agent_id="code-assistant-01",
        action_type=ActionType.FILE_WRITE,
        resource="/workspace/output.txt",
        result="success",
        signature=dummy_signature,
        grant_id="grant-002",
    )

    # Record denied action
    log.record(
        agent_id="code-assistant-01",
        action_type=ActionType.SHELL_EXECUTE,
        resource="rm -rf /",
        result="denied",
        signature=dummy_signature,
        context={"reason": "blocked by policy"},
    )

    # Different agent
    log.record(
        agent_id="data-processor-02",
        action_type=ActionType.API_CALL,
        resource="https://api.example.com/data",
        result="success",
        signature=dummy_signature,
    )

    # Verify chain integrity
    valid, error = log.verify_chain()
    print(f"Chain integrity: {'valid' if valid else f'INVALID - {error}'}")

    # Query by agent
    print(f"\nTotal entries: {len(log)}")

    agent_entries = log.query(agent_id="code-assistant-01")
    print(f"Entries for code-assistant-01: {len(agent_entries)}")

    # Get activity summary
    activity = log.get_agent_activity("code-assistant-01")
    print(f"\nActivity summary:")
    for action, count in activity.items():
        print(f"  {action}: {count}")

    # Export for analysis
    print(f"\nJSON export:")
    print(log.export_json(agent_entries[:2]))
