# Prompt Management (Fragment System)

## Problem

System prompts grow organically and become unmaintainable:

- Copy-pasted sections across different agents
- No versioning or rollback capability
- Difficult to A/B test prompt variations
- Order-dependent assembly breaks silently

## Our Approach

**Database-backed fragments** with a taxonomy (`kind`) and template
expansion syntax.

```python
@dataclass
class PromptFragment:
    id: str
    kind: FragmentKind  # capability, context, parameters, safety, example
    content: str
    order_index: int
    tags: tuple[str, ...]  # "prod", "experimental", etc.
```

Template syntax for dynamic assembly:

- `{fragment:id}` - Insert specific fragment
- `{kind:capability}` - Insert all capability fragments
- `{user_input}` - Insert user's message
- `{date}` - Current date

## Why This Works

**Taxonomy prevents sprawl.** The five `kind` categories force you to
classify each fragment. When reviewing prompts, you can quickly identify
what's a capability vs a safety rule.

**`order_index` is essential.** Prompt assembly must be deterministic.
Without explicit ordering, fragments can be shuffled, causing subtle
behavior changes. We learned this the hard way.

**Tags enable versioning.** The `prod` tag marks production-ready fragments.
You can develop new fragments without affecting live systems, then flip the
tag to deploy.

```python
# Only production fragments
fragments = store.get_production()

# Experimental prompt for A/B testing
fragments = store.get_by_tag("experiment-v2")
```

## Trade-offs

| Decision          | Benefit                    | Cost                        |
| ----------------- | -------------------------- | --------------------------- |
| Database storage  | Versioning, hot-reload     | More infrastructure         |
| Fragment taxonomy | Organized, searchable      | Learning curve              |
| Template syntax   | Flexible composition       | String parsing, debug harder|

### Alternatives Considered

**Inline strings**: Simplest approach but becomes unmaintainable past ~500
lines of system prompt.

**File-based templates**: Middle ground, but no versioning or runtime
modification.

**LangChain PromptTemplate**: Good for simple cases but fragment assembly
and ordering requires custom logic anyway.

## Code Examples

### Python - Fragment Assembly

```python
store = FragmentStore()

# Add fragments with explicit ordering
store.add(PromptFragment(
    id="identity",
    kind=FragmentKind.CONTEXT,
    content="You are a coding assistant.",
    order_index=0,
    tags=("prod",),
))

store.add(PromptFragment(
    id="no-destructive",
    kind=FragmentKind.SAFETY,
    content="Never run rm -rf or similar destructive commands.",
    order_index=100,  # Safety rules come last
    tags=("prod",),
))

# Assemble production prompt
assembler = PromptAssembler(store)
prompt = assembler.assemble_production()
```

### TypeScript - Template Expansion

```typescript
const engine = new TemplateEngine(store);

const template = `
{fragment:identity}

Today: {date}
User: {user_input}

{kind:safety}
`;

const prompt = engine.expand(template, {
  user_input: "Delete all test files",
});
```

## Industry Alignment

Fragment-based prompt assembly is a well-established pattern:

**Frameworks using similar patterns:**

- [Langfuse Prompt Composability][langfuse-compose] - Embeds prompts within
  prompts using `@@@langfusePrompt:name=X@@@` syntax
- [LangChain PipelinePromptTemplate][langchain-pipeline] - Composes prompts
  via the `+` operator and pipeline templates
- [Datasette LLM Fragments][llm-fragments] - Database-backed fragments with
  `-f/--fragment` CLI options
- [DSPy Signatures][dspy-sigs] - Declarative prompt modules with field ordering
- [PromptLayer][promptlayer] - Advocates "modular task-based prompts" over
  monolithic master prompts

**Our `order_index` approach is more robust than most.** LangChain relies on
operator order, Datasette uses argument order. Explicit numeric ordering:

- Allows inserting fragments without renumbering
- Enables non-contiguous numbering (0, 10, 100) for future additions
- Is deterministic regardless of insertion order

**Versioning validation:**

- [Langfuse A/B Testing][langfuse-ab] uses labels (`prod-a`, `prod-b`)
- [Braintrust][braintrust] provides side-by-side comparison and CI/CD
- [Helicone][helicone] offers automatic versioning on code changes

Our tag-based approach (`prod`, `experimental`) aligns with these patterns.

[langfuse-compose]: https://langfuse.com/docs/prompt-management/features/composability
[langchain-pipeline]: https://python.langchain.com/v0.2/docs/how_to/prompts_composition/
[llm-fragments]: https://llm.datasette.io/en/stable/fragments.html
[dspy-sigs]: https://dspy.ai/learn/programming/signatures/
[promptlayer]: https://blog.promptlayer.com/prompt-routers-and-modular-prompt-architecture-8691d7a57aee/
[langfuse-ab]: https://langfuse.com/docs/prompt-management/features/a-b-testing
[braintrust]: https://www.braintrust.dev/articles/ab-testing-llm-prompts
[helicone]: https://www.braintrust.dev/articles/best-prompt-versioning-tools-2025

## Files

- `python/fragments.py` - Fragment model and store
- `python/template_engine.py` - Template variable expansion
- `typescript/fragments.ts` - Fragment types and assembler
- `typescript/templateEngine.ts` - Type-safe template engine
