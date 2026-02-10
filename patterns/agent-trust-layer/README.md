# Agent Trust Layer

## Problem

Agents with tool access inherit user credentials, creating systemic risk:

- **No agent identity** - Agents act as the user, not as themselves
- **Unbounded permissions** - One-time grants persist indefinitely
- **No provenance** - Can't verify where a skill or tool came from
- **No attribution** - Can't determine which agent performed which action

When agents can install packages, execute code, or access APIs, the blast
radius of a compromised agent equals the blast radius of a compromised user.

## Our Approach

**Cryptographic identity per agent** with scoped, time-bound, revocable grants.

```python
@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    public_key: bytes
    issuer: str
    created_at: datetime

@dataclass(frozen=True)
class Grant:
    grant_id: str
    agent_id: str
    scope: str              # e.g., "file:read:/tmp/*"
    expires_at: datetime
    revoked: bool = False
```

Four components:

1. **Identity** - Each agent has a keypair; actions are signed
2. **Grants** - Scoped permissions with expiration
3. **Provenance** - Skills/tools are signed by publishers
4. **Audit Log** - Immutable record of agent actions

## Why This Works

**Agent identity enables attribution.** When every action is signed, you can
trace "who deleted that file?" to a specific agent, not just "the AI did it."

**Time-bound grants limit blast radius.** A grant that expires in 1 hour
can't be exploited next week. Default-deny with explicit grants beats
default-allow with blocklists.

**Provenance verification catches supply chain attacks.** Skills are code
disguised as data. Requiring signatures from known publishers prevents
loading untrusted code.

**Immutable audit logs enable forensics.** When something goes wrong, you
can reconstruct exactly what happened and which agent is responsible.

## Trade-offs

| Decision            | Benefit                      | Cost                          |
| ------------------- | ---------------------------- | ----------------------------- |
| Cryptographic keys  | Non-repudiation, attribution | Key management complexity     |
| Time-bound grants   | Limited blast radius         | Grant renewal overhead        |
| Signature checks    | Supply chain security        | Publisher onboarding friction |
| Append-only logs    | Tamper-evident audit         | Storage growth                |

### Alternatives Considered

**Capability tokens**: Pass opaque tokens instead of checking grants. More
elegant but harder to revoke and audit.

**OAuth scopes**: Reuse existing OAuth infrastructure. Considered but agents
need finer-grained, shorter-lived grants than typical OAuth flows.

**Process isolation**: Sandbox each agent in a container. Adds operational
complexity; doesn't solve attribution or provenance.

## Code Examples

### Python - Agent Identity and Grants

```python
# Create an agent with cryptographic identity
identity = create_agent_identity(
    agent_id="code-assistant-01",
    issuer="my-org"
)

# Issue a scoped, time-bound grant
grant = issue_grant(
    agent_id=identity.agent_id,
    scope="file:write:/workspace/*",
    ttl_seconds=3600  # 1 hour
)

# Check permission before action
if check_grant(store, identity.agent_id, "file:write:/workspace/main.py"):
    # Perform action and log it
    audit_log.record(
        agent_id=identity.agent_id,
        action="file:write",
        resource="/workspace/main.py",
        signature=sign_action(identity, action_data)
    )
```

### TypeScript - Provenance Verification

```typescript
// Verify a skill before loading
const skill = await loadSkill("publisher/code-formatter");

const verification = verifyProvenance(skill, {
  trustedPublishers: ["verified-org", "official-tools"],
  requireSignature: true,
});

if (!verification.valid) {
  throw new Error(`Untrusted skill: ${verification.reason}`);
}

// Skill is safe to load
registerSkill(skill);
```

### Config - Grant Policies

```yaml
grant_policies:
  default:
    max_ttl_seconds: 3600        # 1 hour max
    require_scope: true          # No wildcard grants

  scopes:
    file:read:
      max_ttl_seconds: 86400     # 24 hours for read

    file:write:
      max_ttl_seconds: 3600      # 1 hour for write
      require_confirmation: true

    shell:execute:
      max_ttl_seconds: 300       # 5 minutes
      require_confirmation: true
      audit_level: VERBOSE

provenance:
  require_signature: true
  trusted_publishers:
    - "org-verified"
    - "official-tools"
  blocked_publishers:
    - "unknown"
```

## Industry Alignment

This pattern addresses gaps identified in emerging agent security frameworks:

**Identity and attribution:**

- [OWASP Top 10 for LLM Applications][owasp-llm] - Lists "Excessive Agency"
  and privilege escalation as top concerns
- [AWS Agentic AI Security Matrix][aws-security] - Recommends "identity and
  access management" as a core security dimension
- [NIST AI Risk Management Framework][nist-ai] - Calls for "traceability"
  and "accountability" in AI systems

**Time-bound and revocable access:**

- [Google Cloud IAM Conditions][gcp-iam] - Supports time-based access with
  automatic expiration
- [AWS IAM Session Policies][aws-sessions] - Temporary credentials scoped
  to specific sessions
- [Zero Trust Architecture (NIST SP 800-207)][nist-zero-trust] - "Never
  trust, always verify" with continuous authorization

**Supply chain security:**

- [SLSA Framework][slsa] - Supply chain Levels for Software Artifacts;
  provenance and build integrity
- [Sigstore][sigstore] - Keyless signing for software artifacts
- [SBOM (Software Bill of Materials)][sbom] - Tracking component provenance

**Key industry observations:**

- Most agent frameworks inherit user credentials without agent-specific identity
- Permission grants are typically permanent until manually revoked
- Few frameworks verify provenance of skills, plugins, or tools
- Audit logs often lack cryptographic attribution

[owasp-llm]: https://owasp.org/www-project-top-10-for-large-language-model-applications/
[aws-security]: https://aws.amazon.com/blogs/security/the-agentic-ai-security-matrix-a-framework-for-securing-autonomous-ai-systems/
[nist-ai]: https://www.nist.gov/itl/ai-risk-management-framework
[gcp-iam]: https://cloud.google.com/iam/docs/conditions-overview
[aws-sessions]: https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session
[nist-zero-trust]: https://csrc.nist.gov/publications/detail/sp/800-207/final
[slsa]: https://slsa.dev/
[sigstore]: https://www.sigstore.dev/
[sbom]: https://www.cisa.gov/sbom

## Files

- `python/identity.py` - Agent identity with key generation
- `python/grants.py` - Time-bound grant management
- `python/provenance.py` - Skill signature verification
- `python/audit.py` - Append-only audit log
- `typescript/identity.ts` - Agent identity management
- `typescript/grants.ts` - Grant issuance and checking
- `typescript/provenance.ts` - Provenance verification
- `typescript/audit.ts` - Audit logging
