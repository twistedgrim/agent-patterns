# Agent Personas & Mode Configuration

## Problem

LLM agents need consistent personalities and behaviors across sessions.
Without structured personas:

- Prompts become scattered and inconsistent
- Tool permissions vary unpredictably
- Mode-specific constraints (investigation vs autonomous) are hardcoded

## Our Approach

**Dataclass/Interface-based personas** with a registry pattern for
centralized management.

```python
@dataclass(frozen=True)
class AgentPersona:
    name: str
    persona_type: PersonaType
    system_prompt: str
    max_tool_calls: int = 10
    allowed_tools: tuple[str, ...] = ()
```

Key design decisions:

1. **Frozen dataclasses** - Personas are immutable after creation
2. **Registry pattern** - Lookup by name, no hardcoded references
3. **Mode configs** - Separate constraints from persona definitions

## Why This Works

**Immutability prevents bugs.** When a persona is passed through multiple
handlers, you know it won't be mutated. The `with_tool_limit()` method
creates new instances instead of modifying.

**Registry enables runtime flexibility.** Personas can be loaded from config
files, databases, or registered at startup. Code references personas by
name, not direct import.

**Mode separation is essential.** The same "coder" persona behaves
differently in `conversation` mode (3 tool calls, confirmation required) vs
`autonomous` mode (50 tool calls, no confirmation). Separating mode config
from persona definition prevents combinatorial explosion.

## Trade-offs

| Decision           | Benefit                  | Cost                         |
| ------------------ | ------------------------ | ---------------------------- |
| Static personas    | Predictable, testable    | Less dynamic adaptation      |
| Registry pattern   | Decoupled lookup         | Indirection, missing errors  |
| Frozen dataclasses | Thread-safe, no mutation | More memory for `with_*`     |

### Alternatives Considered

**Dynamic prompt injection**: Modify system prompts at runtime based on
context. We rejected this because it makes behavior unpredictable and hard
to debug.

**Single monolithic config**: One large config object for everything.
Rejected because personas and modes have different lifecycles and ownership.

## Code Examples

### Python - Persona with Mode Routing

```python
orchestrator = Orchestrator(default_mode=AgentMode.CONVERSATION)

# Mode determines effective constraints
persona = orchestrator.get_active_persona()
# -> AgentPersona(name="default", max_tool_calls=3, ...)

orchestrator.set_mode(AgentMode.AUTONOMOUS)
persona = orchestrator.get_active_persona()
# -> AgentPersona(name="coder", max_tool_calls=50, ...)
```

### TypeScript - Type-Safe Mode Handling

```typescript
const orchestrator = new Orchestrator("conversation");

// TypeScript ensures mode is valid at compile time
orchestrator.setMode("autonomous"); // OK
orchestrator.setMode("invalid"); // Compile error

const persona = orchestrator.getActivePersona();
// Type: AgentPersona with all fields guaranteed
```

## Industry Alignment

This pattern aligns with established industry practices:

**Frameworks using similar patterns:**

- [Microsoft Azure AI Agent Design Patterns][ms-patterns] - Documents the
  "Coordinator" pattern for routing requests to specialized agents
- [OpenAI Agents SDK][openai-agents] - Uses orchestrator agents with sub-agents
  exposed as tools
- [LangChain Subagents][langchain-subagents] - Supports static and dynamic
  registry patterns for agent lookup
- [Google Cloud Agentic AI Patterns][gcp-patterns] - Describes coordinator
  agents that decompose and dispatch tasks

**Mode routing validation:**

Our three-mode approach maps to the "Levels of AI Agent Autonomy" framework:

- `conversation` → L1-L2 (Executor/Actor) - Limited tools, confirmation required
- `investigation` → L3 (Operator) - Auto-investigate, still confirms
- `autonomous` → L4-L5 (Explorer/Inventor) - Full autonomy

See [Levels of Autonomy for AI Agents][autonomy-levels] and
[Vellum's Agentic Behavior Guide][vellum-levels].

**Key validations:**

- Immutable personas with copy-on-modify is a recognized best practice
- Registry pattern is standard across LangChain, Microsoft, and OpenAI SDKs
- Mode-based routing appears in Claude Code (`permission_mode`) and AutoGPT

[ms-patterns]: https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns
[openai-agents]: https://openai.github.io/openai-agents-python/multi_agent/
[langchain-subagents]: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
[gcp-patterns]: https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system
[autonomy-levels]: https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1
[vellum-levels]: https://www.vellum.ai/blog/levels-of-agentic-behavior

## Files

- `python/personas.py` - Dataclass personas with registry
- `python/orchestrator.py` - Mode-based routing
- `typescript/personas.ts` - Interface personas with registry
- `typescript/orchestrator.ts` - Mode routing with type safety
