"""
Agent Framework Integration - Python Conceptual Example

OpenCode is TypeScript-first. This file shows the conceptual equivalent
patterns for Python, which you'd implement with a framework like Aider
or a custom solution using the patterns from this repo.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Callable


class EventType(Enum):
    """Events emitted by a coding agent framework."""
    SESSION_CREATED = "session.created"
    MESSAGE_UPDATED = "message.updated"
    FILE_DIFF = "session.diff"
    SESSION_IDLE = "session.idle"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Event from the agent framework."""
    type: EventType
    session_id: str
    properties: dict


@dataclass
class ModelConfig:
    """Model configuration for the agent."""
    provider_id: str
    model_id: str


@dataclass
class Session:
    """An agent session with conversation state."""
    id: str
    title: str


class CodingAgentFramework(ABC):
    """
    Abstract interface for coding agent frameworks.

    This represents what OpenCode provides in TypeScript.
    In Python, you'd either:
    1. Use a framework like Aider
    2. Build this using the other patterns in this repo
    """

    @abstractmethod
    async def create_session(self, title: str) -> Session:
        """Create a new conversation session."""
        ...

    @abstractmethod
    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        model: ModelConfig,
    ) -> None:
        """Send a prompt to the agent."""
        ...

    @abstractmethod
    async def get_messages(self, session_id: str) -> list[dict]:
        """Get all messages in a session."""
        ...

    @abstractmethod
    async def subscribe_events(self) -> AsyncIterator[AgentEvent]:
        """Subscribe to real-time events."""
        ...


class MockCodingAgent(CodingAgentFramework):
    """
    Mock implementation showing the interface.

    In practice, this would be backed by:
    - Aider's API
    - A custom implementation using patterns from this repo
    - An HTTP client to an agent service
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[dict]] = {}
        self._counter = 0

    async def create_session(self, title: str) -> Session:
        self._counter += 1
        session = Session(id=f"session_{self._counter}", title=title)
        self._sessions[session.id] = session
        self._messages[session.id] = []
        return session

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        model: ModelConfig,
    ) -> None:
        # In reality, this would call the LLM and execute tools
        self._messages[session_id].append({
            "role": "user",
            "content": prompt,
        })
        self._messages[session_id].append({
            "role": "assistant",
            "content": f"[Mock response from {model.provider_id}/{model.model_id}]",
        })

    async def get_messages(self, session_id: str) -> list[dict]:
        return self._messages.get(session_id, [])

    async def subscribe_events(self) -> AsyncIterator[AgentEvent]:
        # In reality, this would be a websocket or SSE stream
        yield AgentEvent(
            type=EventType.SESSION_IDLE,
            session_id="",
            properties={},
        )


# Integration patterns
async def polling_integration(agent: CodingAgentFramework, prompt: str) -> str:
    """
    Integration Pattern 1: Polling

    Simple approach - send prompt, poll for completion.
    """
    session = await agent.create_session("Polling Task")

    await agent.send_prompt(
        session.id,
        prompt,
        ModelConfig(provider_id="anthropic", model_id="claude-3-opus"),
    )

    # Poll until we get a response
    messages = await agent.get_messages(session.id)
    for msg in messages:
        if msg.get("role") == "assistant":
            return msg.get("content", "")

    return ""


async def event_streaming_integration(
    agent: CodingAgentFramework,
    prompt: str,
    on_file_change: Callable[[str], None] | None = None,
) -> str:
    """
    Integration Pattern 2: Event Streaming

    Subscribe to events for real-time updates.
    """
    session = await agent.create_session("Streaming Task")

    # Start event subscription
    events = agent.subscribe_events()

    # Send prompt
    await agent.send_prompt(
        session.id,
        prompt,
        ModelConfig(provider_id="anthropic", model_id="claude-3-opus"),
    )

    # Process events
    async for event in events:
        if event.type == EventType.FILE_DIFF and on_file_change:
            on_file_change(event.properties.get("path", ""))

        if event.type == EventType.SESSION_IDLE:
            break

    # Get final response
    messages = await agent.get_messages(session.id)
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return msg.get("content", "")

    return ""


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        agent = MockCodingAgent()

        # Polling approach
        response = await polling_integration(
            agent,
            "Create a hello world function",
        )
        print(f"Polling response: {response}")

        # Streaming approach with file change callback
        def on_file(path: str):
            print(f"File changed: {path}")

        response = await event_streaming_integration(
            agent,
            "Create a Python module",
            on_file_change=on_file,
        )
        print(f"Streaming response: {response}")

    asyncio.run(main())
