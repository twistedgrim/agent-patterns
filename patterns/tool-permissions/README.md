# Tool Permissions

## Problem

LLM agents with tool access can cause real damage:

- `rm -rf /` is just a string to the model
- Reading `.env` files leaks secrets
- Database writes can corrupt data
- No built-in concept of "this is dangerous"

## Our Approach

**Risk-based permission tiers** with glob pattern matching and conditional
overrides.

```yaml
tools:
  bash:
    default_risk: HIGH
    rules:
      - pattern: "ls *"
        risk: LOW
      - pattern: "rm -rf *"
        risk: CRITICAL
        allowed: false
```

Four risk levels:

- **LOW**: Read-only, no side effects
- **MEDIUM**: Reversible changes
- **HIGH**: Significant changes, hard to reverse
- **CRITICAL**: Destructive or irreversible

The evaluator checks operations against an `max_allowed_risk` threshold.

## Why This Works

**Risk tiers are intuitive.** Developers immediately understand that
CRITICAL > HIGH > MEDIUM > LOW. No need to learn a complex permission model.

**Glob patterns are flexible.** Match paths, commands, or any string
argument. `**/.env*` catches `.env`, `.env.local`, `foo/.env.production`.

**Hot-reload enables runtime updates.** Edit `tools.yaml`, permissions
change immediately. No restart needed. Essential for incident response.

**Conditional overrides handle edge cases.** Some operations are safe in
certain contexts:

```yaml
- pattern: "DELETE *"
  risk: MEDIUM  # Lower risk when...
  condition: "context.table == 'temp_logs'"  # ...deleting temp data
```

## Trade-offs

| Decision      | Benefit             | Cost                          |
| ------------- | ------------------- | ----------------------------- |
| Glob patterns | Flexible, familiar  | Hard to audit, order-dependent|
| Risk levels   | Simple mental model | Coarse-grained (4 levels)     |
| Hot-reload    | Fast policy changes | File watching overhead        |
| YAML config   | Human-readable      | Parsing, no type checking     |

### Alternatives Considered

**Allowlist only**: Explicitly list every allowed operation. Too restrictive
for general-purpose agents.

**Capability-based security**: More principled but harder to implement and
understand.

**ML-based risk scoring**: Score each operation with a model. Adds latency
and unpredictability.

## Code Examples

### Python - Permission Check

```python
evaluator = PermissionEvaluator(max_allowed_risk=RiskLevel.MEDIUM)
evaluator.load_from_yaml("config/tools.yaml")

# Safe operation
result = check_permission(evaluator, "bash", "ls -la")
# -> PermissionResult(allowed=True, risk_level=LOW, ...)

# Dangerous operation
result = check_permission(evaluator, "bash", "rm -rf /")
# -> PermissionResult(allowed=False, risk_level=CRITICAL, ...)

# Needs confirmation
result = check_permission(evaluator, "file_write", "/app/config.json")
# -> PermissionResult(allowed=True, requires_confirmation=True, ...)
```

### TypeScript - With Context

```typescript
const evaluator = new PermissionEvaluator(RiskLevel.MEDIUM);
evaluator.loadFromYaml("config/tools.yaml");

// Context can lower risk for specific cases
const result = evaluator.evaluate("database", "DELETE * FROM logs", {
  table: "temp_logs",
  user: "cleanup_job",
});
```

### Config - Common Patterns

```yaml
tools:
  bash:
    rules:
      # Allow read-only git commands
      - pattern: "git status*"
        risk: LOW
      - pattern: "git log*"
        risk: LOW
      - pattern: "git diff*"
        risk: LOW

      # Require confirmation for writes
      - pattern: "git commit*"
        risk: MEDIUM
        confirm: true
      - pattern: "git push*"
        risk: HIGH
        confirm: true

      # Block dangerous operations
      - pattern: "git push --force*"
        risk: CRITICAL
        allowed: false
```

## Industry Alignment

Risk-tiered permissions are strongly validated by security frameworks:

**Security standards recommending this approach:**

- [OWASP Top 10 for LLM Applications 2025][owasp-llm] - Calls out "elevated
  privileges" and "excessive agency" as top concerns
- [AWS Agentic AI Security Matrix][aws-security] - Recommends categorizing
  operations by risk level for autonomous systems
- [Microsoft Runtime Risk Defense][ms-security] - Advocates "risk-based
  conditional access" with real-time decisions

**Frameworks implementing similar patterns:**

- [LangChain Guardrails][langchain-guardrails] - Human approval for "financial
  transactions, deleting/modifying production data"
- [NVIDIA NeMo Guardrails][nemo] - Topic control, PII detection, jailbreak
  prevention
- [CrewAI][crewai] - `code_execution_mode: "safe"` with `max_execution_time`
- [Superagent Safety Agent][superagent] - Policy enforcement layer evaluating
  actions before execution

**Hot-reload validation:**

- [iamai AI Toolkit][iamai] - "Automatic hot reload" for plugin/config updates
- [Microsoft Dev Proxy][dev-proxy] - "Configuration hot reload" watching files
- [OpenTelemetry Collector][otel] - Hot reload via SIGHUP signal

**Key industry statistics:**

- 87% of enterprises lack comprehensive AI security frameworks (Gartner)
- Gartner predicts: "Through 2029, over 50% of successful attacks against AI
  agents will exploit access control issues"

[owasp-llm]: https://www.trydeepteam.com/docs/frameworks-owasp-top-10-for-llms
[aws-security]: https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/
[ms-security]: https://www.microsoft.com/en-us/security/blog/2026/01/23/runtime-risk-realtime-defense-securing-ai-agents/
[langchain-guardrails]: https://docs.langchain.com/oss/python/langchain/guardrails
[nemo]: https://developer.nvidia.com/nemo-guardrails
[crewai]: https://docs.crewai.com/en/concepts/agents
[superagent]: https://www.helpnetsecurity.com/2025/12/29/superagent-framework-guardrails-agentic-ai/
[iamai]: https://iamai.is-a.dev/en/latest/pages/advanced/hot-reload.html
[dev-proxy]: https://devblogs.microsoft.com/microsoft365dev/dev-proxy-v2-1-with-configuration-hot-reload-and-stdio-proxying/
[otel]: https://last9.io/blog/hot-reload-for-opentelemetry-collector/

## Files

- `python/permissions.py` - Permission evaluator with hot-reload
- `python/config/tools.yaml` - Tool permission rules
- `typescript/permissions.ts` - Type-safe permission system
- `typescript/config/tools.yaml` - Tool permission rules
