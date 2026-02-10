"""
Skill/tool provenance verification.

Verifies that skills and tools come from trusted publishers
before allowing them to be loaded or executed.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import hashlib
import hmac


class VerificationStatus(Enum):
    VERIFIED = "verified"
    UNSIGNED = "unsigned"
    INVALID_SIGNATURE = "invalid_signature"
    UNTRUSTED_PUBLISHER = "untrusted_publisher"
    EXPIRED = "expired"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Publisher:
    """A trusted publisher of skills/tools."""

    publisher_id: str
    name: str
    public_key: bytes
    verified_at: datetime
    trust_level: str = "standard"  # standard, elevated, system


@dataclass(frozen=True)
class SkillManifest:
    """Manifest describing a skill with provenance information."""

    skill_id: str
    name: str
    version: str
    publisher_id: str
    content_hash: bytes
    signature: Optional[bytes] = None
    signed_at: Optional[datetime] = None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    """Result of provenance verification."""

    status: VerificationStatus
    skill_id: str
    publisher: Optional[Publisher] = None
    reason: Optional[str] = None

    @property
    def valid(self) -> bool:
        return self.status == VerificationStatus.VERIFIED


class ProvenanceVerifier:
    """Verifies provenance of skills and tools."""

    def __init__(self, require_signature: bool = True) -> None:
        self._publishers: dict[str, Publisher] = {}
        self._blocked_publishers: set[str] = set()
        self._require_signature = require_signature

    def register_publisher(self, publisher: Publisher) -> None:
        """Register a trusted publisher."""
        self._publishers[publisher.publisher_id] = publisher

    def block_publisher(self, publisher_id: str) -> None:
        """Block a publisher from being trusted."""
        self._blocked_publishers.add(publisher_id)

    def unblock_publisher(self, publisher_id: str) -> None:
        """Remove publisher from blocklist."""
        self._blocked_publishers.discard(publisher_id)

    def verify(self, manifest: SkillManifest, content: bytes) -> VerificationResult:
        """Verify a skill's provenance."""
        # Check if publisher is blocked
        if manifest.publisher_id in self._blocked_publishers:
            return VerificationResult(
                status=VerificationStatus.BLOCKED,
                skill_id=manifest.skill_id,
                reason=f"Publisher {manifest.publisher_id} is blocked",
            )

        # Check if signature is required but missing
        if self._require_signature and manifest.signature is None:
            return VerificationResult(
                status=VerificationStatus.UNSIGNED,
                skill_id=manifest.skill_id,
                reason="Signature required but not provided",
            )

        # Get publisher
        publisher = self._publishers.get(manifest.publisher_id)
        if publisher is None:
            return VerificationResult(
                status=VerificationStatus.UNTRUSTED_PUBLISHER,
                skill_id=manifest.skill_id,
                reason=f"Publisher {manifest.publisher_id} not in trust store",
            )

        # Verify content hash
        actual_hash = hashlib.sha256(content).digest()
        if actual_hash != manifest.content_hash:
            return VerificationResult(
                status=VerificationStatus.INVALID_SIGNATURE,
                skill_id=manifest.skill_id,
                publisher=publisher,
                reason="Content hash mismatch",
            )

        # Verify signature if present
        if manifest.signature:
            if not self._verify_signature(
                publisher.public_key, manifest.content_hash, manifest.signature
            ):
                return VerificationResult(
                    status=VerificationStatus.INVALID_SIGNATURE,
                    skill_id=manifest.skill_id,
                    publisher=publisher,
                    reason="Signature verification failed",
                )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            skill_id=manifest.skill_id,
            publisher=publisher,
        )

    def _verify_signature(
        self, public_key: bytes, content_hash: bytes, signature: bytes
    ) -> bool:
        """
        Verify signature using public key.

        Simplified HMAC verification - use proper asymmetric crypto in production.
        """
        expected = hmac.new(public_key, content_hash, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)


def compute_content_hash(content: bytes) -> bytes:
    """Compute hash of skill content."""
    return hashlib.sha256(content).digest()


def sign_content(private_key: bytes, content_hash: bytes) -> bytes:
    """Sign content hash with private key."""
    return hmac.new(private_key, content_hash, hashlib.sha256).digest()


# Example usage
if __name__ == "__main__":
    verifier = ProvenanceVerifier(require_signature=True)

    # Register trusted publisher
    publisher_private_key = b"publisher-secret-key-12345678901"
    publisher_public_key = hashlib.sha256(publisher_private_key).digest()

    publisher = Publisher(
        publisher_id="official-tools",
        name="Official Tools Publisher",
        public_key=publisher_public_key,
        verified_at=datetime.utcnow(),
        trust_level="elevated",
    )
    verifier.register_publisher(publisher)

    # Create a signed skill
    skill_content = b"""
    name: code-formatter
    description: Formats code according to style guidelines
    commands:
      - format_file
      - check_style
    """

    content_hash = compute_content_hash(skill_content)
    signature = sign_content(publisher_private_key, content_hash)

    manifest = SkillManifest(
        skill_id="code-formatter-v1",
        name="Code Formatter",
        version="1.0.0",
        publisher_id="official-tools",
        content_hash=content_hash,
        signature=signature,
        signed_at=datetime.utcnow(),
    )

    # Verify the skill
    result = verifier.verify(manifest, skill_content)
    print(f"Verification status: {result.status.value}")
    print(f"Valid: {result.valid}")
    if result.publisher:
        print(f"Publisher: {result.publisher.name}")

    # Try with tampered content
    tampered_content = skill_content + b"\n  - malicious_command"
    tampered_result = verifier.verify(manifest, tampered_content)
    print(f"\nTampered content status: {tampered_result.status.value}")
    print(f"Reason: {tampered_result.reason}")

    # Try with untrusted publisher
    untrusted_manifest = SkillManifest(
        skill_id="sketchy-tool",
        name="Sketchy Tool",
        version="1.0.0",
        publisher_id="unknown-publisher",
        content_hash=content_hash,
        signature=signature,
    )
    untrusted_result = verifier.verify(untrusted_manifest, skill_content)
    print(f"\nUntrusted publisher status: {untrusted_result.status.value}")
    print(f"Reason: {untrusted_result.reason}")
