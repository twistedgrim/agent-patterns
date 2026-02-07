"""
Agent Personas Pattern - Python Implementation

Dataclass-based persona definitions with registry for lookup/registration.
Inspired by production patterns from LLM agent systems.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PersonaType(Enum):
    """Available persona types for the agent."""
    ASSISTANT = "assistant"
    INVESTIGATOR = "investigator"
    CODER = "coder"
    ANALYST = "analyst"


@dataclass(frozen=True)
class AgentPersona:
    """
    Defines an agent's personality, capabilities, and constraints.

    Frozen dataclass ensures personas are immutable after creation,
    preventing accidental mutation during runtime.
    """
    name: str
    persona_type: PersonaType
    system_prompt: str
    max_tool_calls: int = 10
    response_style: str = "concise"
    temperature: float = 0.7
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)

    def with_tool_limit(self, limit: int) -> "AgentPersona":
        """Create a new persona with adjusted tool limit."""
        return AgentPersona(
            name=self.name,
            persona_type=self.persona_type,
            system_prompt=self.system_prompt,
            max_tool_calls=limit,
            response_style=self.response_style,
            temperature=self.temperature,
            allowed_tools=self.allowed_tools,
        )


class PersonaRegistry:
    """
    Registry pattern for persona management.

    Centralizes persona definitions and enables runtime lookup
    without hardcoding persona references throughout the codebase.
    """

    _personas: dict[str, AgentPersona] = {}

    @classmethod
    def register(cls, persona: AgentPersona) -> None:
        """Register a persona by name."""
        cls._personas[persona.name] = persona

    @classmethod
    def get(cls, name: str) -> Optional[AgentPersona]:
        """Retrieve a persona by name."""
        return cls._personas.get(name)

    @classmethod
    def list_all(cls) -> list[str]:
        """List all registered persona names."""
        return list(cls._personas.keys())


# Default persona definitions
DEFAULT_PERSONAS = [
    AgentPersona(
        name="default",
        persona_type=PersonaType.ASSISTANT,
        system_prompt="You are a helpful assistant.",
        max_tool_calls=5,
        response_style="concise",
    ),
    AgentPersona(
        name="investigator",
        persona_type=PersonaType.INVESTIGATOR,
        system_prompt="You investigate problems deeply. Ask clarifying questions.",
        max_tool_calls=15,
        response_style="thorough",
        allowed_tools=("search", "read_file", "web_fetch"),
    ),
    AgentPersona(
        name="coder",
        persona_type=PersonaType.CODER,
        system_prompt="You write clean, tested code. Explain your changes.",
        max_tool_calls=20,
        response_style="technical",
        temperature=0.3,
        allowed_tools=("read_file", "write_file", "run_tests", "search"),
    ),
]

# Register defaults on module load
for persona in DEFAULT_PERSONAS:
    PersonaRegistry.register(persona)
