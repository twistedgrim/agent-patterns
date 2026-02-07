"""
SDK Events Pattern - Python Implementation

Uses event streaming for real-time updates from the agent.
"""

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator

PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")
MODEL = os.environ.get("AGENT_MODEL", "claude-3-opus")


class EventType(str, Enum):
    """Event types from the agent."""
    SESSION_STATUS = "session.status"
    SESSION_DIFF = "session.diff"
    MESSAGE_PART_UPDATED = "message.part.updated"
    MESSAGE_UPDATED = "message.updated"
    SESSION_IDLE = "session.idle"
    ERROR = "error"


@dataclass
class AgentEvent:
    """An event from the agent stream."""
    type: EventType
    session_id: str | None = None
    content: str | None = None
    text: str | None = None
    path: str | None = None
    properties: dict | None = None


class EventStreamClient:
    """
    Agent client with event streaming support.
    """

    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}
        self._counter = 0
        self._event_queue: asyncio.Queue[AgentEvent] = asyncio.Queue()

    async def create_session(self, title: str) -> str:
        """Create a new session, returns session ID."""
        self._counter += 1
        session_id = f"session_{self._counter}"
        self._sessions[session_id] = []
        return session_id

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        provider: str,
        model: str,
    ) -> None:
        """Send prompt and emit events."""
        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        # Emit status event
        await self._event_queue.put(AgentEvent(
            type=EventType.SESSION_STATUS,
            session_id=session_id,
        ))

        # Simulate streaming response
        response_parts = [
            "Processing",
            " your",
            " request",
            "...",
        ]

        for part in response_parts:
            await asyncio.sleep(0.1)
            await self._event_queue.put(AgentEvent(
                type=EventType.MESSAGE_PART_UPDATED,
                session_id=session_id,
                text=part,
            ))

        # Store complete message
        self._sessions[session_id].append({
            "role": "user",
            "content": prompt,
        })
        self._sessions[session_id].append({
            "role": "assistant",
            "content": f"Response to: {prompt[:50]}",
        })

        # Emit completion events
        await self._event_queue.put(AgentEvent(
            type=EventType.MESSAGE_UPDATED,
            session_id=session_id,
        ))
        await self._event_queue.put(AgentEvent(
            type=EventType.SESSION_IDLE,
            session_id=session_id,
        ))

    async def subscribe_events(self) -> AsyncIterator[AgentEvent]:
        """Subscribe to event stream."""
        while True:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=60.0,
                )
                yield event

                # Stop on idle or error
                if event.type in (EventType.SESSION_IDLE, EventType.ERROR):
                    break
            except asyncio.TimeoutError:
                break

    async def get_messages(self, session_id: str) -> list[dict]:
        """Get session messages."""
        return self._sessions.get(session_id, [])


async def run_sdk_with_events(prompt: str) -> str:
    """
    SDK usage with event streaming.

    Subscribes to events for real-time feedback.
    """
    print("Starting Agent SDK with event subscription...")
    print(f"Provider: {PROVIDER}, Model: {MODEL}")

    client = EventStreamClient()

    # Create session
    session_id = await client.create_session("SDK Events POC")
    print(f"Session created: {session_id}")

    # Collect response
    response_text = ""

    # Start event processing
    async def process_events():
        nonlocal response_text
        print("Subscribing to events...")

        async for event in client.subscribe_events():
            print(f"Event: {event.type.value}")

            if event.session_id == session_id:
                if event.text:
                    response_text += event.text
                if event.content:
                    response_text += event.content

            if event.type == EventType.SESSION_IDLE:
                print("Session complete (idle)")
                break

            if event.type == EventType.ERROR:
                raise RuntimeError(f"Event error: {event.properties}")

    # Run prompt and event processing concurrently
    print("Sending prompt...")
    await asyncio.gather(
        client.send_prompt(session_id, prompt, PROVIDER, MODEL),
        process_events(),
    )

    # If no text from events, get from messages
    if not response_text:
        print("No text from events, checking messages...")
        messages = await client.get_messages(session_id)
        for msg in messages:
            if msg.get("role") == "assistant":
                response_text = msg.get("content", "")
                break

    return response_text or "No response received"


async def stream_events_example():
    """Demonstrate streaming events with callbacks."""
    client = EventStreamClient()
    session_id = await client.create_session("Stream Demo")

    events_received = []

    async def on_event(event: AgentEvent):
        events_received.append(event.type)
        if event.type == EventType.MESSAGE_PART_UPDATED:
            print(event.text, end="", flush=True)

    # Process events with callback
    event_task = asyncio.create_task(_process_with_callback(
        client.subscribe_events(),
        on_event,
    ))

    await client.send_prompt(session_id, "Hello!", PROVIDER, MODEL)
    await event_task

    print(f"\nEvents received: {[e.value for e in events_received]}")


async def _process_with_callback(
    events: AsyncIterator[AgentEvent],
    callback: callable,
):
    """Helper to process events with callback."""
    async for event in events:
        await callback(event)
        if event.type == EventType.SESSION_IDLE:
            break


# CLI runner
if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello"

    print("=" * 50)
    print("SDK Events POC")
    print("=" * 50)
    print(f"Prompt: {prompt}")
    print()

    async def main():
        try:
            response = await run_sdk_with_events(prompt)
            print()
            print("=" * 50)
            print("RESPONSE:")
            print("=" * 50)
            print(response)

            print()
            print("=" * 50)
            print("STREAMING DEMO:")
            print("=" * 50)
            await stream_events_example()
        except Exception as e:
            print(f"\nERROR: {e}")
            raise SystemExit(1)

    asyncio.run(main())
