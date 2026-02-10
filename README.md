# Agent Patterns

Configuration patterns for building LLM agents, extracted from production
systems.

## Overview

This repository documents battle-tested patterns for agent configuration.
Each pattern includes:

- **Problem** - What this pattern solves
- **Our Approach** - How we implemented it
- **Why This Works** - Opinions on the design
- **Trade-offs** - What we gave up and alternatives considered
- **Code Examples** - Minimal Python and TypeScript implementations

## Patterns

### [Agent Personas](./patterns/agent-personas/)

Dataclass-based persona definitions with mode routing.

```python
@dataclass(frozen=True)
class AgentPersona:
    name: str
    system_prompt: str
    max_tool_calls: int = 10
```

**Key insight**: Mode-specific constraints (`max_tool_calls`) prevent runaway
agents. Static personas with a registry beats hardcoded prompts.

### [Prompt Management](./patterns/prompt-management/)

Database-backed prompt fragments with taxonomy and template expansion.

```python
class FragmentKind(Enum):
    CAPABILITY = "capability"
    CONTEXT = "context"
    SAFETY = "safety"
```

**Key insight**: Fragment taxonomy (`kind`) enables reuse without prompt
sprawl. `order_index` for deterministic assembly is essential.

### [Context Layering](./patterns/context-layering/)

Priority-based context assembly with token budgets.

```text
System (P100) → Memory (P80) → History (P60) → Supplemental (P40)
```

**Key insight**: When you hit token limits, you know system prompts stay and
old history gets truncated. Vector memory improves coherence without full
history.

### [Provider Abstraction](./patterns/provider-abstraction/)

YAML-driven model registry with semantic aliases.

```yaml
aliases:
  primary: claude-3-opus     # Complex tasks
  fast: claude-3-haiku       # Simple tasks
  cheap: gpt-3.5-turbo       # Bulk operations
```

**Key insight**: Code uses intent (`primary`), not implementation
(`claude-3-opus`). Cost tracking enables budget-aware model selection.

### [Tool Permissions](./patterns/tool-permissions/)

Risk-based permission tiers with glob patterns.

```yaml
- pattern: "rm -rf *"
  risk: CRITICAL
  allowed: false
```

**Key insight**: Four risk levels (LOW → CRITICAL) are intuitive. Hot-reload
enables runtime policy changes without restarts.

### [Agent Framework Integration](./patterns/agent-framework-integration/)

Integrate with coding agent SDKs like OpenCode instead of building from
scratch.

```typescript
const { client, server } = await createOpencode();
const session = await client.session.create({ body: { title: "Task" } });
await client.session.prompt({
  path: { id: session.data.id },
  body: {
    parts: [{ type: "text", text: prompt }],
    model: { providerID: "anthropic", modelID: "claude-3-opus" },
  },
});
```

**Key insight**: For coding agents, frameworks provide session management,
file operations, and provider flexibility. Build your own for simpler use
cases or when you need fine-grained control.

### [Agent Trust Layer](./patterns/agent-trust-layer/)

Cryptographic identity, scoped grants, and provenance verification for
agents acting on behalf of users.

```python
# Issue a time-bound, revocable grant
grant = store.issue(
    agent_id="code-assistant-01",
    scope="file:write:/workspace/*",
    ttl_seconds=3600,  # Expires in 1 hour
    issuer="admin"
)

# Verify before action
if store.check(agent_id, "file:write:/workspace/main.py"):
    audit_log.record(agent_id, action, resource, signature)
```

**Key insight**: Agents need their own identity, not inherited user
credentials. Time-bound grants limit blast radius. Provenance verification
catches supply chain attacks on skills and tools.

## Directory Structure

```text
agent-patterns/
├── README.md
├── patterns/
│   ├── agent-personas/
│   │   ├── README.md
│   │   ├── python/
│   │   │   ├── personas.py
│   │   │   └── orchestrator.py
│   │   └── typescript/
│   │       ├── personas.ts
│   │       └── orchestrator.ts
│   ├── prompt-management/
│   │   └── ...
│   ├── context-layering/
│   │   └── ...
│   ├── provider-abstraction/
│   │   └── ...
│   ├── tool-permissions/
│   │   └── ...
│   ├── agent-framework-integration/
│   │   └── ...
│   └── agent-trust-layer/
│       ├── README.md
│       ├── python/
│       │   ├── identity.py
│       │   ├── grants.py
│       │   ├── provenance.py
│       │   └── audit.py
│       └── typescript/
│           ├── identity.ts
│           ├── grants.ts
│           ├── provenance.ts
│           └── audit.ts
```

## Design Philosophy

### Minimal Illustrative Examples

Each pattern is 50-100 lines showing the core idea. These aren't
production-ready libraries—they're blueprints you adapt to your needs.

### Opinions Over Neutrality

We document what works and why, including trade-offs. "Fragment taxonomy
prevents sprawl" is more useful than "you can organize prompts various ways."

### Dual Language Support

Python and TypeScript implementations for each pattern. Same concepts,
idiomatic to each language.

## Key Learnings

### What We Got Right

1. **Immutable configurations** - Personas, fragments, and permissions are
   immutable. No mutation bugs, easy to test, thread-safe.

2. **Registry patterns** - Centralized lookup by name decouples code from
   specific implementations. Change YAML, not code.

3. **Layered architecture** - Context layers, risk tiers, and fragment kinds
   provide structure without rigidity.

4. **Hot-reload capability** - Runtime configuration changes without restarts
   are essential for iteration and incident response.

### What We'd Do Differently

1. **Earlier cost tracking** - We added cost tracking late. Build it in from
   the start.

2. **Better condition expressions** - Our condition evaluation is basic. A
   proper expression parser would handle more cases.

3. **Typed configurations** - YAML is convenient but loses type safety.
   Consider JSON Schema or TypeScript-first configs.

## Usage

Each pattern stands alone. Copy the files you need and adapt to your codebase.

```bash
# Python dependencies (optional, for YAML parsing)
pip install pyyaml

# TypeScript dependencies (optional)
npm install yaml
```

## License

MIT
