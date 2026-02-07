"""
Context Layering Pattern - Python Implementation

Builds layered context: System → Memory → History → Query.
Manages token budgets and priority-based inclusion.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal


class ContextPriority(IntEnum):
    """Priority levels for context inclusion (higher = more important)."""
    SYSTEM = 100      # Always included
    MEMORY = 80       # Semantic memory from vector store
    HISTORY = 60      # Recent conversation
    SUPPLEMENTAL = 40 # Optional context


MessageRole = Literal["system", "user", "assistant"]


@dataclass
class Message:
    """A single message in the context."""
    role: MessageRole
    content: str
    priority: ContextPriority = ContextPriority.HISTORY
    token_count: int = 0

    def __post_init__(self):
        if self.token_count == 0:
            # Rough estimate: 4 chars per token
            self.token_count = len(self.content) // 4


@dataclass
class ContextLayer:
    """A layer of context with metadata."""
    name: str
    messages: list[Message] = field(default_factory=list)
    priority: ContextPriority = ContextPriority.HISTORY

    @property
    def total_tokens(self) -> int:
        return sum(m.token_count for m in self.messages)


class ContextBuilder:
    """
    Builds context by assembling layers within token budget.

    Layers are added in priority order. When budget is exceeded,
    lower-priority content is truncated first.
    """

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.layers: dict[str, ContextLayer] = {}

    def add_layer(self, name: str, priority: ContextPriority) -> "ContextBuilder":
        """Add a named layer with priority."""
        self.layers[name] = ContextLayer(name=name, priority=priority)
        return self

    def add_message(
        self,
        layer: str,
        role: MessageRole,
        content: str,
    ) -> "ContextBuilder":
        """Add a message to a layer."""
        if layer not in self.layers:
            raise ValueError(f"Unknown layer: {layer}")

        msg = Message(role=role, content=content, priority=self.layers[layer].priority)
        self.layers[layer].messages.append(msg)
        return self

    def add_system(self, content: str) -> "ContextBuilder":
        """Convenience: add system message to 'system' layer."""
        if "system" not in self.layers:
            self.add_layer("system", ContextPriority.SYSTEM)
        return self.add_message("system", "system", content)

    def add_history(self, role: MessageRole, content: str) -> "ContextBuilder":
        """Convenience: add to 'history' layer."""
        if "history" not in self.layers:
            self.add_layer("history", ContextPriority.HISTORY)
        return self.add_message("history", role, content)

    def build(self) -> list[Message]:
        """
        Assemble all layers into final message list.

        Higher priority layers are preserved; lower priority truncated
        if over budget.
        """
        # Sort layers by priority (highest first)
        sorted_layers = sorted(
            self.layers.values(),
            key=lambda l: l.priority,
            reverse=True,
        )

        result: list[Message] = []
        remaining_tokens = self.max_tokens

        for layer in sorted_layers:
            layer_messages = []
            for msg in layer.messages:
                if msg.token_count <= remaining_tokens:
                    layer_messages.append(msg)
                    remaining_tokens -= msg.token_count
                else:
                    # Truncate this layer, skip remaining messages
                    break
            result.extend(layer_messages)

        # Sort final result: system first, then by original order
        system_msgs = [m for m in result if m.role == "system"]
        other_msgs = [m for m in result if m.role != "system"]
        return system_msgs + other_msgs

    def to_api_format(self) -> list[dict]:
        """Convert to API message format."""
        return [{"role": m.role, "content": m.content} for m in self.build()]


# Example usage
if __name__ == "__main__":
    builder = ContextBuilder(max_tokens=2000)

    # Build layered context
    context = (
        builder
        .add_layer("system", ContextPriority.SYSTEM)
        .add_layer("memory", ContextPriority.MEMORY)
        .add_layer("history", ContextPriority.HISTORY)
        .add_system("You are a helpful assistant.")
        .add_message("memory", "system", "User prefers concise answers.")
        .add_history("user", "What is Python?")
        .add_history("assistant", "Python is a programming language.")
        .add_history("user", "Show me an example.")
        .build()
    )

    for msg in context:
        print(f"[{msg.role}] {msg.content[:50]}...")
