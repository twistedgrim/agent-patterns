# Context Layering

## Problem

LLM context is a finite resource. Without structure:

- Important context gets pushed out by verbose history
- No control over what gets included when truncating
- Vector memory and conversation history compete unpredictably

## Our Approach

**Layered context assembly** with explicit priorities and token budgets.

```text
┌─────────────────────────────┐
│  System Prompt (Priority 100)│ ← Always included
├─────────────────────────────┤
│  Vector Memory (Priority 80) │ ← Relevant past context
├─────────────────────────────┤
│  Conversation (Priority 60)  │ ← Recent history
├─────────────────────────────┤
│  Supplemental (Priority 40)  │ ← Optional extras
└─────────────────────────────┘
```

When token budget is exceeded, lower priority layers are truncated first.

```python
builder = ContextBuilder(max_tokens=8000)
builder.add_layer("system", ContextPriority.SYSTEM)
builder.add_layer("memory", ContextPriority.MEMORY)
builder.add_layer("history", ContextPriority.HISTORY)
```

## Why This Works

**Explicit priorities prevent surprises.** When you hit 8K tokens, you know
the system prompt stays and old history gets truncated. No guessing.

**Semantic memory improves coherence.** The LLM "remembers" relevant past
interactions without including entire conversation history. This is
essential for long-running agents.

**Token budget forces discipline.** Knowing you have a budget makes you
write concise prompts. The `THREAD_HISTORY_LIMIT` pattern (e.g., last 10
messages) prevents unbounded growth.

## Trade-offs

| Decision              | Benefit             | Cost                       |
| --------------------- | ------------------- | -------------------------- |
| Fixed priority levels | Predictable, simple | Less flexible than dynamic |
| Token estimation      | Fast (char/4)       | ~20% error vs tokenizer    |
| Memory as system msgs | LLM treats as truth | Can't mark as fuzzy recall |

### Alternatives Considered

**Dynamic priority scoring**: Score each message by relevance to current
query. Rejected because it adds latency and complexity for marginal benefit.

**Sliding window only**: Just keep last N messages. Rejected because system
prompt and relevant memories are more important than recency.

**Tokenizer integration**: Use tiktoken/etc for exact counts. We use
estimation for speed but recommend exact counting in production.

## Code Examples

### Python - Layered Context Building

```python
builder = ContextBuilder(max_tokens=4000)

# Define layers with priorities
builder.add_layer("system", ContextPriority.SYSTEM)
builder.add_layer("memory", ContextPriority.MEMORY)
builder.add_layer("history", ContextPriority.HISTORY)

# Add content
builder.add_system("You are a coding assistant.")
builder.add_message("memory", "system", "User prefers Python.")
builder.add_history("user", "Help me write a function")
builder.add_history("assistant", "Sure, here's an example...")

# Build respects token budget
messages = builder.to_api_format()
```

### TypeScript - Memory Augmentation

```typescript
const store = new MockVectorStore();
await store.add("User prefers detailed explanations");
await store.add("User is working on a Discord bot");

const memory = new MemoryAugmentedContext(store, {
  maxMemories: 3,
  similarityThreshold: 0.1,
});

const builder = new ContextBuilder(4000);
builder.addSystem("You are a helpful assistant.");

// Augment with relevant memories based on query
await memory.augmentContext(builder, "How do I add slash commands?");

builder.addHistory("user", "How do I add slash commands?");
const messages = builder.toApiFormat();
```

## Industry Alignment

Priority-based context assembly is a well-documented pattern:

**Frameworks validating this approach:**

- [GitHub's Prompt Engineering Guide][github-prompt] - Describes sorting by
  priority and "deleting lowest priority wishes until what remains fits"
- [OpenAI Model Spec][openai-spec] - Confirms models give "different levels of
  priority to messages with different roles"
- [LangChain Context Engineering][langchain-context] - Documents layered
  context with system instructions, short-term memory, long-term memory, and
  retrieved knowledge

**Our layer ordering matches industry standard:**

| Our Layer    | Industry Equivalent           |
|--------------|-------------------------------|
| System (100) | System Instructions           |
| Memory (80)  | Long-term Memory / RAG        |
| History (60) | Short-term / Conversation     |
| Supplemental | Tool outputs, extras          |

**Token budget management:**

- [Maxim AI][maxim-context] - "Dynamic Context Allocation" adjusting based on
  query complexity
- [LLM Toolkit Course][llm-toolkit] - `TokenBudgetManager` class pattern
  matching our `ContextBuilder`
- [LangChain Memory][langchain-memory] - `ConversationBufferWindowMemory` for
  sliding window, `trim_messages` for truncation

**Vector memory validation:**

- [Pinecone + LangChain Guide][pinecone-memory] - Standard pattern for RAG
- [LangMem Conceptual Guide][langmem] - Documents memory as dedicated layer

[github-prompt]: https://github.blog/ai-and-ml/generative-ai/prompt-engineering-guide-generative-ai-llms/
[openai-spec]: https://platform.openai.com/docs/guides/prompt-engineering
[langchain-context]: https://docs.langchain.com/oss/python/langchain/context-engineering
[maxim-context]: https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/
[llm-toolkit]: https://apxml.com/courses/getting-started-with-llm-toolkit/chapter-3-context-and-token-management/managing-token-budgets
[langchain-memory]: https://python.langchain.com/docs/modules/memory/types/buffer/
[pinecone-memory]: https://www.pinecone.io/learn/series/langchain/langchain-conversational-memory/
[langmem]: https://langchain-ai.github.io/langmem/concepts/conceptual_guide/

## Files

- `python/context_builder.py` - Layered context with priorities
- `python/memory_integration.py` - Vector store integration
- `typescript/contextBuilder.ts` - Type-safe context builder
- `typescript/memoryIntegration.ts` - Async memory augmentation
