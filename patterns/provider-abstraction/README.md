# Provider Abstraction

## Problem

Hardcoding model names throughout your codebase creates problems:

- Changing models requires finding/replacing across files
- No visibility into costs until the bill arrives
- Provider-specific code scattered everywhere
- Testing with cheaper models is awkward

## Our Approach

**YAML-driven model registry** with an alias system that decouples code
from specific models.

```yaml
# models.yaml
models:
  claude-3-opus:
    provider: anthropic
    model_id: claude-3-opus-20240229
    cost_per_1k_input: 0.015
    # ...

aliases:
  primary: claude-3-opus    # Complex tasks
  fast: claude-3-haiku      # Simple tasks
  cheap: gpt-3.5-turbo      # Bulk operations
```

Code uses aliases:

```python
model = registry.resolve("primary")  # Returns claude-3-opus config
```

Swap models by editing YAML, not code.

## Why This Works

**Aliases create semantic intent.** When you write `registry.resolve("fast")`,
you're expressing intent ("I need low latency"), not implementation
("use claude-3-haiku"). This survives model deprecations.

**Cost tracking enables budget control.** By tracking tokens per model, you
can set alerts, compare costs across tasks, and make informed decisions
about which alias to use.

```python
tracker.record_usage("primary", input_tokens=1000, output_tokens=500)
print(f"Total cost: ${tracker.get_total_cost():.4f}")
```

**Provider configs centralize API details.** API base URLs, auth environment
variables, and other provider-specific details live in one place.

## Trade-offs

| Decision           | Benefit                 | Cost                        |
| ------------------ | ----------------------- | --------------------------- |
| YAML config        | Easy to edit, no code   | Runtime parsing, YAML errors|
| Alias indirection  | Semantic intent, swap   | One more lookup             |
| Registry singleton | Global access           | Harder to test, global state|

### Alternatives Considered

**Environment variables only**: Simple but doesn't capture model metadata
(context window, costs). Rejected for lack of expressiveness.

**LangChain model abstraction**: Good but heavyweight. Our pattern is ~100
lines and does exactly what we need.

**Database storage**: Overkill for model config that changes infrequently.
YAML works well for < 50 models.

## Code Examples

### Python - Using Aliases

```python
registry = ModelRegistry()
registry.load_from_yaml("config/models.yaml")

# Use semantic aliases
primary = registry.resolve("primary")
fast = registry.resolve("fast")

# Choose model based on task complexity
def get_model_for_task(complexity: str) -> ModelConfig:
    if complexity == "high":
        return registry.resolve("primary")
    elif complexity == "low":
        return registry.resolve("fast")
    else:
        return registry.resolve("balanced")
```

### TypeScript - Cost Tracking

```typescript
const registry = new ModelRegistry();
registry.loadFromYaml("config/models.yaml");

const tracker = new CostTracker(registry);

// After each API call
tracker.recordUsage("primary", inputTokens, outputTokens);

// Check budget
if (tracker.getTotalCost() > 10.0) {
  console.warn("Budget exceeded!");
}

// Get breakdown
const summary = tracker.getSummary();
// { "primary": { inputTokens: 5000, outputTokens: 2000, cost: 0.225 } }
```

### Config - Model Selection Strategy

```yaml
# Different aliases for different environments
aliases:
  # Production: quality matters
  primary: claude-3-opus

  # Development: cost matters
  # primary: claude-3-haiku

  # A/B testing: try new model
  # primary: claude-3-5-sonnet-20241022
```

## Industry Alignment

YAML-driven model registries and semantic aliases are industry standard:

**Frameworks using similar patterns:**

- [LiteLLM][litellm] - YAML config with `model_alias` for mapping user-facing
  names to backend models, plus routing strategies
- [Arch Gateway][arch-gateway] - Explicitly supports `fast-model`,
  `smart-model`, `creative-model` aliases
- [LM Studio][lm-studio] - `model.yaml` as open standard for AI model config
- [Portkey AI Gateway][portkey] - 200+ providers with unified API abstraction
- [Datasette LLM][llm-aliases] - `llm aliases set <alias> <model-id>` CLI

**Semantic aliases are explicitly recommended:**

> "Model literals, semantic aliases, and preference-aligned routing for LLMs"
> — [Hacker News discussion on model routing][hn-discussion]

**Cost tracking is essential:**

- [Langfuse][langfuse-cost] - Automatic cost calculation with model pricing
- [LangSmith][langsmith-cost] - Cost aggregation per trace
- [Helicone][helicone-cost] - Monitoring and optimization for cost control
- [Portkey][portkey-usage] - Usage dashboards and spend forecasting

Industry consensus: "The only way to control LLM costs is to track token
usage and attribute it to specific dimensions" — [Traceloop][traceloop]

Our lightweight ~100 line approach is a valid trade-off vs heavyweight
frameworks like LangChain when you need exactly this functionality.

[litellm]: https://docs.litellm.ai/docs/routing
[arch-gateway]: https://docs.archgw.com/concepts/llm_providers/model_aliases.html
[lm-studio]: https://lmstudio.ai/docs/app/modelyaml
[portkey]: https://github.com/Portkey-AI/gateway
[llm-aliases]: https://llm.datasette.io/en/stable/aliases.html
[hn-discussion]: https://news.ycombinator.com/item?id=45337201
[langfuse-cost]: https://langfuse.com/docs/observability/features/token-and-cost-tracking
[langsmith-cost]: https://docs.langchain.com/langsmith/cost-tracking
[helicone-cost]: https://www.helicone.ai/blog/monitor-and-optimize-llm-costs
[portkey-usage]: https://portkey.ai/blog/tracking-llm-token-usage-across-providers-teams-and-workloads/
[traceloop]: https://www.traceloop.com/blog/from-bills-to-budgets-how-to-track-llm-token-usage-and-cost-per-user

## Files

- `python/registry.py` - Model registry and cost tracker
- `python/config/models.yaml` - Model configuration
- `typescript/registry.ts` - Type-safe registry
- `typescript/config/models.yaml` - Model configuration
