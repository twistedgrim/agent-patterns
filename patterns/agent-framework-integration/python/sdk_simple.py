"""
SDK Simple Pattern - Python Implementation

Uses an agent SDK with polling for responses.
This demonstrates the basic SDK integration pattern.
"""

import asyncio
import os
from dataclasses import dataclass

# Configuration
PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")
MODEL = os.environ.get("AGENT_MODEL", "claude-3-opus")


@dataclass
class Message:
    """A message in the conversation."""
    role: str
    content: str


@dataclass
class Session:
    """An agent session."""
    id: str
    title: str


class AgentClient:
    """
    Mock agent SDK client.

    Replace with actual SDK (e.g., httpx client to agent API).
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self._sessions: dict[str, list[Message]] = {}
        self._counter = 0

    async def create_session(self, title: str) -> Session:
        """Create a new session."""
        self._counter += 1
        session_id = f"session_{self._counter}"
        self._sessions[session_id] = []
        return Session(id=session_id, title=title)

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        provider: str,
        model: str,
    ) -> None:
        """Send a prompt to the session."""
        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        self._sessions[session_id].append(Message(role="user", content=prompt))

        # Simulate API call delay
        await asyncio.sleep(0.1)

        # Mock response
        response = f"[Response from {provider}/{model}]: Processed '{prompt[:50]}...'"
        self._sessions[session_id].append(Message(role="assistant", content=response))

    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages in a session."""
        return self._sessions.get(session_id, [])


async def run_sdk_simple(prompt: str) -> str:
    """
    Simple SDK usage with polling.

    Creates a session, sends prompt, polls for response.
    """
    print("Starting Agent SDK...")
    print(f"Provider: {PROVIDER}, Model: {MODEL}")

    client = AgentClient()

    # Create session
    session = await client.create_session("SDK POC Test")
    print(f"Session created: {session.id}")

    # Send prompt
    print("Sending prompt...")
    await client.send_prompt(
        session_id=session.id,
        prompt=prompt,
        provider=PROVIDER,
        model=MODEL,
    )
    print("Prompt sent, waiting for response...")

    # Poll for response
    response = await wait_for_response(client, session.id)
    return response


async def wait_for_response(
    client: AgentClient,
    session_id: str,
    timeout_seconds: float = 120.0,
    poll_interval: float = 2.0,
) -> str:
    """
    Poll session messages until assistant response is found.
    """
    start_time = asyncio.get_event_loop().time()
    last_count = 0

    while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
        await asyncio.sleep(poll_interval)

        messages = await client.get_messages(session_id)

        if len(messages) > last_count:
            print(f"Messages: {len(messages)}")
            last_count = len(messages)

        # Look for assistant response
        for msg in messages:
            if msg.role == "assistant" and msg.content:
                return msg.content

        elapsed = int(asyncio.get_event_loop().time() - start_time)
        print(f"Polling... {elapsed}s elapsed")

    raise TimeoutError(f"No response after {timeout_seconds}s")


# CLI runner
if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello and tell me what model you are."

    print("=" * 50)
    print("SDK Simple POC")
    print("=" * 50)
    print(f"Prompt: {prompt}")
    print()

    async def main():
        try:
            response = await run_sdk_simple(prompt)
            print()
            print("=" * 50)
            print("RESPONSE:")
            print("=" * 50)
            print(response)
        except Exception as e:
            print(f"\nERROR: {e}")
            raise SystemExit(1)

    asyncio.run(main())
