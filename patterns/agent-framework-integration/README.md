# Agent Framework Integration

## Problem

Building a coding agent from scratch requires:

- Provider abstraction and model management
- Session and conversation state
- Tool execution and file operations
- Event streaming for real-time feedback
- Sandboxing and security

This is significant infrastructure. For coding agents specifically,
frameworks like OpenCode provide these capabilities out of the box.

## Our Approach

**Integrate with existing agent SDKs** rather than building from scratch.
OpenCode provides:

- Embedded server with local development feel
- Session-based conversation management
- File operations as first-class primitives
- Event streaming for real-time updates
- Provider/model flexibility at runtime

```typescript
import { createOpencode } from "@opencode-ai/sdk";

const { client, server } = await createOpencode();
const session = await client.session.create({ body: { title: "My Task" } });

await client.session.prompt({
  path: { id: session.data.id },
  body: {
    parts: [{ type: "text", text: "Create a Python function..." }],
    model: { providerID: "anthropic", modelID: "claude-3-opus" },
  },
});
```

## Integration Approaches

### 1. CLI Integration (Simplest)

Shell out to `opencode run` for fire-and-forget tasks:

```typescript
const { stdout } = await execAsync(
  `cat prompt.txt | opencode run --model ${MODEL}`
);
```

**Use when**: Simple one-off tasks, scripting, no streaming needed.

### 2. SDK with Polling

Create sessions and poll for completion:

```typescript
const session = await client.session.create({ body: { title: "Task" } });
await client.session.prompt({ path: { id: sessionId }, body: { ... } });

// Poll for response
while (!complete) {
  const messages = await client.session.messages({ path: { id: sessionId } });
  // Check for assistant response...
}
```

**Use when**: Simple integration, don't need real-time streaming.

### 3. SDK with Event Streaming

Subscribe to events for real-time updates:

```typescript
const eventStream = await client.event.subscribe();

for await (const event of eventStream.stream) {
  if (event.type === "session.diff") {
    console.log(`File: ${event.properties.path}`);
  }
  if (event.type === "session.idle") {
    break; // Complete
  }
}
```

**Use when**: Need real-time feedback, file operation tracking, progress.

### 4. File Operations

OpenCode handles file creation/modification as part of the agent loop:

```typescript
const prompt = `Create a Python file at ${targetFile} that:
1. Defines a greet(name) function
2. Has a main block that calls greet("World")`;

await client.session.prompt({ ... });

// OpenCode creates the file - check it exists
if (existsSync(targetFile)) {
  const content = await readFile(targetFile, "utf-8");
}
```

**Use when**: Coding tasks that produce file artifacts.

## Why This Works

**Local development feel.** The embedded server runs locally, files are
created in your filesystem, and the experience mirrors interactive
development.

**Provider flexibility.** Swap models via `providerID`/`modelID` without
code changes:

```typescript
model: { providerID: "anthropic", modelID: "claude-3-opus" }
// or
model: { providerID: "openai", modelID: "gpt-4-turbo" }
```

**Session state management.** Conversations persist within sessions,
enabling multi-turn interactions without manual context management.

**Event-driven architecture.** Real-time events (`session.diff`,
`message.updated`, `session.idle`) enable responsive UIs and progress
tracking.

## Trade-offs

| Decision            | Benefit              | Cost                         |
| ------------------- | -------------------- | ---------------------------- |
| Use SDK vs build    | Fast to production   | Less control, SDK lock-in    |
| Embedded server     | Local dev experience | Process management overhead  |
| Event streaming     | Real-time feedback   | Complexity vs polling        |
| Session abstraction | Automatic state      | Less visibility into context |

### When to Use a Framework

**Use an SDK like OpenCode when:**

- Building a coding agent (file operations are core)
- Need quick time-to-production
- Provider flexibility matters
- Don't want to build session/context management

**Build your own when:**

- Simple chat/completion (no tools)
- Need fine-grained control over prompts
- Non-coding use cases
- Custom tool implementations

## Files

### TypeScript (OpenCode SDK)

- `typescript/cli-simple.ts` - CLI integration via `opencode run`
- `typescript/sdk-simple.ts` - SDK with polling
- `typescript/sdk-session.ts` - Session-based SDK usage
- `typescript/sdk-events.ts` - Event streaming integration
- `typescript/sdk-file-create.ts` - File creation demonstration

### Python (Mock SDK)

- `python/cli_simple.py` - CLI integration via subprocess
- `python/sdk_simple.py` - SDK with polling
- `python/sdk_session.py` - Session-based SDK usage
- `python/sdk_events.py` - Event streaming integration
- `python/sdk_file_create.py` - File creation demonstration
- `python/conceptual.py` - Abstract interfaces and framework patterns

## Industry Alignment

Agent SDK integration is the recommended approach for coding agents:

**Frameworks validating this approach:**

- [Rivet Sandbox Agent SDK][rivet] - Provides tool registration, file
  operations, and sandboxed execution for autonomous coding
- [Google Agent Development Kit (ADK)][google-adk] - Session-based agent
  framework with event streaming and multi-turn support
- [AWS Bedrock AgentCore][bedrock] - Production agent framework emphasizing
  session management and tool orchestration
- [OpenAI Agents SDK][openai-agents] - "The Agent SDK has a very small
  surface area" - intentionally thin wrapper over capabilities

**Session-based architecture is standard:**

- [Claude Code SDK][claude-sdk] - Session abstraction with conversation
  persistence and context management
- [Aider][aider] - Architect/Editor pattern: one model plans, another edits
- [Continue.dev][continue] - IDE-integrated coding agent with session state

**Event streaming preference:**

Industry consensus favors SSE (Server-Sent Events) over polling for agent
feedback. This enables:

- Real-time file diff visualization
- Progress indicators during long operations
- Immediate error surfacing

**Build vs Buy decision framework:**

The [Anthropic Guide to Building Effective Agents][anthropic-guide]
recommends: "Consider starting with simple prompts and direct API calls...
Add complexity only when simpler solutions fall short."

Our examples show the spectrum from CLI (simplest) to full SDK integration,
letting you choose the right abstraction level.

[rivet]: https://rivet.dev/docs/sdk/agent-sdk
[google-adk]: https://google.github.io/adk-docs/
[bedrock]: https://aws.amazon.com/bedrock/agentcore/
[openai-agents]: https://openai.github.io/openai-agents-python/
[claude-sdk]: https://docs.anthropic.com/en/docs/claude-code/sdk
[aider]: https://aider.chat/docs/usage/modes.html
[continue]: https://docs.continue.dev/
[anthropic-guide]: https://www.anthropic.com/engineering/building-effective-agents

## Python Notes

The Python examples use mock implementations since OpenCode is TypeScript-
first. The patterns are identical - replace the mock clients with:

- **Aider** - Use `aider.coders` module or CLI subprocess
- **Custom HTTP client** - Connect to any agent API
- **LangChain agents** - Wrap LangChain agent executor
