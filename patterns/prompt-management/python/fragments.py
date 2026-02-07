"""
Prompt Fragment System - Python Implementation

Database-backed prompt fragments with taxonomy and template expansion.
Enables reusable, versioned prompt components.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FragmentKind(Enum):
    """Taxonomy of prompt fragment types."""
    CAPABILITY = "capability"  # What the agent can do
    CONTEXT = "context"        # Background information
    PARAMETERS = "parameters"  # Configuration/constraints
    SAFETY = "safety"          # Safety guidelines
    EXAMPLE = "example"        # Few-shot examples


@dataclass
class PromptFragment:
    """
    A reusable prompt component.

    Fragments are building blocks assembled into full prompts.
    The `order_index` ensures deterministic assembly order.
    """
    id: str
    kind: FragmentKind
    content: str
    order_index: int
    tags: tuple[str, ...] = ()
    version: int = 1

    @property
    def is_production(self) -> bool:
        """Check if fragment is tagged for production use."""
        return "prod" in self.tags


class FragmentStore:
    """
    In-memory fragment store (replace with database in production).

    Supports lookup by ID, kind filtering, and tag-based queries.
    """

    def __init__(self):
        self._fragments: dict[str, PromptFragment] = {}

    def add(self, fragment: PromptFragment) -> None:
        self._fragments[fragment.id] = fragment

    def get(self, fragment_id: str) -> Optional[PromptFragment]:
        return self._fragments.get(fragment_id)

    def get_by_kind(self, kind: FragmentKind) -> list[PromptFragment]:
        """Get all fragments of a specific kind, ordered by order_index."""
        matches = [f for f in self._fragments.values() if f.kind == kind]
        return sorted(matches, key=lambda f: f.order_index)

    def get_production(self) -> list[PromptFragment]:
        """Get all production-tagged fragments, ordered."""
        matches = [f for f in self._fragments.values() if f.is_production]
        return sorted(matches, key=lambda f: f.order_index)


class PromptAssembler:
    """
    Assembles fragments into complete prompts.

    Handles template syntax expansion:
    - {fragment:id} - Insert fragment by ID
    - {kind:type} - Insert all fragments of a kind
    """

    def __init__(self, store: FragmentStore):
        self.store = store

    def assemble(self, fragment_ids: list[str]) -> str:
        """Assemble fragments by ID list into a single prompt."""
        parts = []
        for fid in fragment_ids:
            fragment = self.store.get(fid)
            if fragment:
                parts.append(fragment.content)
        return "\n\n".join(parts)

    def assemble_by_kind(self, kinds: list[FragmentKind]) -> str:
        """Assemble all fragments of specified kinds."""
        parts = []
        for kind in kinds:
            for fragment in self.store.get_by_kind(kind):
                parts.append(fragment.content)
        return "\n\n".join(parts)

    def assemble_production(self) -> str:
        """Assemble all production-tagged fragments."""
        fragments = self.store.get_production()
        return "\n\n".join(f.content for f in fragments)


# Example usage
if __name__ == "__main__":
    store = FragmentStore()

    # Register fragments
    store.add(PromptFragment(
        id="core-identity",
        kind=FragmentKind.CONTEXT,
        content="You are a helpful coding assistant.",
        order_index=0,
        tags=("prod",),
    ))
    store.add(PromptFragment(
        id="tool-usage",
        kind=FragmentKind.CAPABILITY,
        content="You can read and write files, search code, and run tests.",
        order_index=10,
        tags=("prod",),
    ))
    store.add(PromptFragment(
        id="safety-rules",
        kind=FragmentKind.SAFETY,
        content="Never execute destructive commands without confirmation.",
        order_index=100,
        tags=("prod",),
    ))

    assembler = PromptAssembler(store)
    prompt = assembler.assemble_production()
    print(prompt)
