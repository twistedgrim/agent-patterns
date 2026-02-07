"""
SDK Session Pattern - Python Implementation

Demonstrates session-based SDK usage for multi-turn conversations.
"""

import asyncio
import os
from dataclasses import dataclass, field

PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")
MODEL = os.environ.get("AGENT_MODEL", "claude-3-opus")


@dataclass
class Message:
    """A message in the conversation."""
    role: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SessionInfo:
    """Session metadata."""
    id: str
    title: str
    created_at: str = ""
    message_count: int = 0


class SessionClient:
    """
    Session-focused agent client.

    Emphasizes session lifecycle and multi-turn conversations.
    """

    def __init__(self):
        self._sessions: dict[str, SessionInfo] = {}
        self._messages: dict[str, list[Message]] = {}
        self._counter = 0

    async def create(self, title: str) -> SessionInfo:
        """Create a new session."""
        self._counter += 1
        session_id = f"sess_{self._counter}"

        info = SessionInfo(
            id=session_id,
            title=title,
            created_at="2024-01-01T00:00:00Z",
        )
        self._sessions[session_id] = info
        self._messages[session_id] = []
        return info

    async def get(self, session_id: str) -> SessionInfo | None:
        """Get session info."""
        info = self._sessions.get(session_id)
        if info:
            info.message_count = len(self._messages.get(session_id, []))
        return info

    async def prompt(
        self,
        session_id: str,
        text: str,
        provider: str = PROVIDER,
        model: str = MODEL,
    ) -> None:
        """Send a prompt to the session."""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        messages = self._messages[session_id]
        messages.append(Message(role="user", content=text))

        # Simulate processing
        await asyncio.sleep(0.1)

        # Generate mock response based on conversation history
        turn = len([m for m in messages if m.role == "user"])
        response = f"[Turn {turn}] Response to: {text[:30]}..."
        messages.append(Message(
            role="assistant",
            content=response,
            metadata={"model": f"{provider}/{model}"},
        ))

    async def messages(self, session_id: str) -> list[Message]:
        """Get all messages in session."""
        return self._messages.get(session_id, [])

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._messages[session_id]
            return True
        return False


async def run_sdk_session(prompt: str) -> str:
    """
    Session-based SDK usage.

    Demonstrates creating a session and having a conversation.
    """
    print("Initializing Session SDK...")

    client = SessionClient()

    # Create session
    session = await client.create("POC Test")
    print(f"Session created: {session.id}")

    # Send prompt
    print("Sending prompt...")
    await client.prompt(
        session_id=session.id,
        text=prompt,
        provider=PROVIDER,
        model=MODEL,
    )
    print("Prompt sent, waiting for response...")

    # Poll for completion
    max_attempts = 60
    for attempt in range(max_attempts):
        await asyncio.sleep(0.5)

        messages = await client.messages(session.id)

        if len(messages) > 1:
            # Find assistant response
            for msg in messages:
                if msg.role == "assistant":
                    return msg.content

        print(f"Polling... attempt {attempt + 1}/{max_attempts}")

    raise TimeoutError("No response received")


async def multi_turn_example():
    """Demonstrate multi-turn conversation."""
    client = SessionClient()

    session = await client.create("Multi-turn Demo")
    print(f"Session: {session.id}")

    # First turn
    await client.prompt(session.id, "What is Python?")
    messages = await client.messages(session.id)
    print(f"Turn 1: {messages[-1].content}")

    # Second turn (context preserved)
    await client.prompt(session.id, "Show me an example")
    messages = await client.messages(session.id)
    print(f"Turn 2: {messages[-1].content}")

    # Check session state
    info = await client.get(session.id)
    print(f"Total messages: {info.message_count}")


# CLI runner
if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello"

    print("Running SDK Session POC...")
    print(f"Provider: {PROVIDER}")
    print(f"Model: {MODEL}")
    print(f"Prompt: {prompt[:100]}...")

    async def main():
        response = await run_sdk_session(prompt)
        print("\n=== RESPONSE ===")
        print(response)

        print("\n=== MULTI-TURN DEMO ===")
        await multi_turn_example()

    asyncio.run(main())
