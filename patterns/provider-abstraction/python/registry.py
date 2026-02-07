"""
Provider Abstraction Pattern - Python Implementation

YAML-driven model registry with alias system and cost tracking.
Decouples code from specific providers/models.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: str       # "anthropic", "openai", "bedrock"
    model_id: str       # "claude-3-opus-20240229"
    display_name: str   # "Claude 3 Opus"
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    supports_tools: bool = True
    supports_vision: bool = False


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    name: str
    api_base: str | None = None
    env_var: str | None = None  # Environment variable for API key


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    def complete(
        self,
        messages: list[dict],
        **kwargs: Any,
    ) -> str:
        """Generate a completion."""
        ...


class ModelRegistry:
    """
    Registry for model configurations with alias support.

    Aliases like 'primary', 'fast', 'cheap' map to actual models,
    enabling easy swapping without code changes.
    """

    def __init__(self):
        self.models: dict[str, ModelConfig] = {}
        self.aliases: dict[str, str] = {}
        self.providers: dict[str, ProviderConfig] = {}

    def load_from_yaml(self, path: str | Path) -> None:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        # Load providers
        for name, config in data.get("providers", {}).items():
            self.providers[name] = ProviderConfig(
                name=name,
                api_base=config.get("api_base"),
                env_var=config.get("env_var"),
            )

        # Load models
        for model_id, config in data.get("models", {}).items():
            self.models[model_id] = ModelConfig(
                provider=config["provider"],
                model_id=config["model_id"],
                display_name=config.get("display_name", model_id),
                context_window=config.get("context_window", 8192),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.0),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.0),
                supports_tools=config.get("supports_tools", True),
                supports_vision=config.get("supports_vision", False),
            )

        # Load aliases
        self.aliases = data.get("aliases", {})

    def resolve(self, name_or_alias: str) -> ModelConfig:
        """Resolve an alias or model name to its configuration."""
        # Check if it's an alias
        model_key = self.aliases.get(name_or_alias, name_or_alias)

        if model_key not in self.models:
            raise KeyError(f"Unknown model: {name_or_alias}")

        return self.models[model_key]

    def get_provider(self, name: str) -> ProviderConfig:
        """Get provider configuration."""
        if name not in self.providers:
            raise KeyError(f"Unknown provider: {name}")
        return self.providers[name]

    def list_models(self) -> list[str]:
        """List all available model keys."""
        return list(self.models.keys())

    def list_aliases(self) -> dict[str, str]:
        """Get alias mappings."""
        return dict(self.aliases)


class CostTracker:
    """Tracks API costs per model."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.usage: dict[str, dict[str, int]] = {}  # model -> {input, output}

    def record_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record token usage and return cost."""
        config = self.registry.resolve(model_name)

        if model_name not in self.usage:
            self.usage[model_name] = {"input": 0, "output": 0}

        self.usage[model_name]["input"] += input_tokens
        self.usage[model_name]["output"] += output_tokens

        cost = (
            (input_tokens / 1000) * config.cost_per_1k_input +
            (output_tokens / 1000) * config.cost_per_1k_output
        )
        return cost

    def get_total_cost(self) -> float:
        """Calculate total cost across all models."""
        total = 0.0
        for model_name, tokens in self.usage.items():
            config = self.registry.resolve(model_name)
            total += (tokens["input"] / 1000) * config.cost_per_1k_input
            total += (tokens["output"] / 1000) * config.cost_per_1k_output
        return total

    def get_summary(self) -> dict[str, Any]:
        """Get usage summary by model."""
        summary = {}
        for model_name, tokens in self.usage.items():
            config = self.registry.resolve(model_name)
            cost = (
                (tokens["input"] / 1000) * config.cost_per_1k_input +
                (tokens["output"] / 1000) * config.cost_per_1k_output
            )
            summary[model_name] = {
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "cost": cost,
            }
        return summary


# Example usage
if __name__ == "__main__":
    registry = ModelRegistry()
    registry.load_from_yaml("config/models.yaml")

    # Use alias to get model
    primary = registry.resolve("primary")
    print(f"Primary model: {primary.display_name}")
    print(f"Provider: {primary.provider}")
    print(f"Cost: ${primary.cost_per_1k_input}/1K input")

    # Track costs
    tracker = CostTracker(registry)
    cost = tracker.record_usage("primary", input_tokens=1000, output_tokens=500)
    print(f"Request cost: ${cost:.4f}")
