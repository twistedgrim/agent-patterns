"""
Agent identity with cryptographic key generation.

Each agent has a unique identity with a keypair for signing actions.
This enables attribution and non-repudiation of agent behavior.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib
import hmac
import secrets


@dataclass(frozen=True)
class AgentIdentity:
    """Immutable agent identity with cryptographic material."""

    agent_id: str
    public_key: bytes
    issuer: str
    created_at: datetime
    metadata: tuple[tuple[str, str], ...] = ()

    def fingerprint(self) -> str:
        """Short identifier derived from public key."""
        return hashlib.sha256(self.public_key).hexdigest()[:16]


@dataclass
class AgentKeyPair:
    """Agent identity with private key for signing."""

    identity: AgentIdentity
    private_key: bytes

    def sign(self, data: bytes) -> bytes:
        """Sign data with agent's private key (HMAC for simplicity)."""
        return hmac.new(self.private_key, data, hashlib.sha256).digest()

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify a signature against this agent's key."""
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)


class IdentityRegistry:
    """Registry for managing agent identities."""

    def __init__(self) -> None:
        self._identities: dict[str, AgentIdentity] = {}
        self._keypairs: dict[str, AgentKeyPair] = {}

    def create_identity(
        self,
        agent_id: str,
        issuer: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> AgentKeyPair:
        """Create a new agent identity with keypair."""
        if agent_id in self._identities:
            raise ValueError(f"Agent {agent_id} already exists")

        # Generate keypair (simplified - use proper crypto in production)
        private_key = secrets.token_bytes(32)
        public_key = hashlib.sha256(private_key).digest()

        identity = AgentIdentity(
            agent_id=agent_id,
            public_key=public_key,
            issuer=issuer,
            created_at=datetime.utcnow(),
            metadata=tuple((metadata or {}).items()),
        )

        keypair = AgentKeyPair(identity=identity, private_key=private_key)

        self._identities[agent_id] = identity
        self._keypairs[agent_id] = keypair

        return keypair

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Retrieve a public identity by agent ID."""
        return self._identities.get(agent_id)

    def get_keypair(self, agent_id: str) -> Optional[AgentKeyPair]:
        """Retrieve keypair for signing (internal use only)."""
        return self._keypairs.get(agent_id)

    def revoke_identity(self, agent_id: str) -> bool:
        """Revoke an agent's identity."""
        if agent_id in self._identities:
            del self._identities[agent_id]
            del self._keypairs[agent_id]
            return True
        return False

    def list_identities(self) -> list[AgentIdentity]:
        """List all registered identities."""
        return list(self._identities.values())


def verify_signature(
    identity: AgentIdentity, data: bytes, signature: bytes, public_key: bytes
) -> bool:
    """
    Verify a signature using only public information.

    In production, use proper asymmetric crypto (Ed25519, RSA).
    This simplified version demonstrates the pattern.
    """
    # Simplified verification - real implementation would use public key crypto
    expected = hmac.new(public_key, data, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


# Example usage
if __name__ == "__main__":
    registry = IdentityRegistry()

    # Create agent identity
    keypair = registry.create_identity(
        agent_id="code-assistant-01",
        issuer="my-organization",
        metadata={"purpose": "code-review", "environment": "production"},
    )

    print(f"Agent ID: {keypair.identity.agent_id}")
    print(f"Fingerprint: {keypair.identity.fingerprint()}")
    print(f"Issuer: {keypair.identity.issuer}")

    # Sign an action
    action_data = b"file:write:/workspace/main.py"
    signature = keypair.sign(action_data)
    print(f"Signature: {signature.hex()[:32]}...")

    # Verify signature
    is_valid = keypair.verify(action_data, signature)
    print(f"Signature valid: {is_valid}")
