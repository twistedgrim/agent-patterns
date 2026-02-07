"""
Agent Orchestrator Pattern - Python Implementation

Mode-based routing that selects appropriate persona and constraints
based on the current agent mode (investigation, autonomous, conversation).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from personas import AgentPersona, PersonaRegistry


class AgentMode(Enum):
    """Operating modes that determine agent behavior."""
    CONVERSATION = "conversation"  # Standard chat, limited tools
    INVESTIGATION = "investigation"  # Deep research, more tool calls
    AUTONOMOUS = "autonomous"  # Full autonomy, maximum tools


@dataclass
class ModeConfig:
    """Configuration constraints for each operating mode."""
    persona_name: str
    max_tool_calls: int
    auto_investigate: bool = False
    require_confirmation: bool = True


# Mode-specific configurations
MODE_CONFIGS: dict[AgentMode, ModeConfig] = {
    AgentMode.CONVERSATION: ModeConfig(
        persona_name="default",
        max_tool_calls=3,
        auto_investigate=False,
        require_confirmation=True,
    ),
    AgentMode.INVESTIGATION: ModeConfig(
        persona_name="investigator",
        max_tool_calls=15,
        auto_investigate=True,
        require_confirmation=True,
    ),
    AgentMode.AUTONOMOUS: ModeConfig(
        persona_name="coder",
        max_tool_calls=50,
        auto_investigate=True,
        require_confirmation=False,
    ),
}


class Orchestrator:
    """
    Routes requests to appropriate persona based on mode.

    The orchestrator acts as the control plane, determining which
    persona handles a request and with what constraints.
    """

    def __init__(self, default_mode: AgentMode = AgentMode.CONVERSATION):
        self.current_mode = default_mode
        self._mode_change_hooks: list[Callable[[AgentMode], None]] = []

    def set_mode(self, mode: AgentMode) -> None:
        """Change the operating mode."""
        self.current_mode = mode
        for hook in self._mode_change_hooks:
            hook(mode)

    def on_mode_change(self, callback: Callable[[AgentMode], None]) -> None:
        """Register a callback for mode changes."""
        self._mode_change_hooks.append(callback)

    def get_active_persona(self) -> AgentPersona:
        """Get the persona for the current mode with applied constraints."""
        config = MODE_CONFIGS[self.current_mode]
        persona = PersonaRegistry.get(config.persona_name)

        if persona is None:
            persona = PersonaRegistry.get("default")

        # Apply mode-specific tool limit
        return persona.with_tool_limit(config.max_tool_calls)

    def should_auto_investigate(self) -> bool:
        """Check if current mode allows automatic investigation."""
        return MODE_CONFIGS[self.current_mode].auto_investigate

    def requires_confirmation(self) -> bool:
        """Check if current mode requires user confirmation for actions."""
        return MODE_CONFIGS[self.current_mode].require_confirmation


# Usage example
if __name__ == "__main__":
    orchestrator = Orchestrator()

    # Get persona for default mode
    persona = orchestrator.get_active_persona()
    print(f"Mode: {orchestrator.current_mode.value}")
    print(f"Persona: {persona.name}, Tools: {persona.max_tool_calls}")

    # Switch to autonomous mode
    orchestrator.set_mode(AgentMode.AUTONOMOUS)
    persona = orchestrator.get_active_persona()
    print(f"Mode: {orchestrator.current_mode.value}")
    print(f"Persona: {persona.name}, Tools: {persona.max_tool_calls}")
