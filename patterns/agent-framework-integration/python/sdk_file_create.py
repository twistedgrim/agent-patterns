"""
SDK File Creation Pattern - Python Implementation

Demonstrates using an agent SDK to create files.
"""

import asyncio
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncIterator

PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")
MODEL = os.environ.get("AGENT_MODEL", "claude-3-opus")
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(os.environ.get("POC_OUTPUT_DIR", SCRIPT_DIR / "output"))


class EventType(str, Enum):
    """Event types from the agent."""
    SESSION_STATUS = "session.status"
    SESSION_DIFF = "session.diff"
    MESSAGE_UPDATED = "message.updated"
    SESSION_IDLE = "session.idle"


@dataclass
class FileEvent:
    """A file operation event."""
    type: EventType
    path: str | None = None
    content: str | None = None


class FileCreationClient:
    """
    Agent client that can create files.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self._sessions: dict[str, list[dict]] = {}
        self._counter = 0
        self._event_queue: asyncio.Queue[FileEvent] = asyncio.Queue()

    async def create_session(self, title: str) -> str:
        """Create a new session."""
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
        """Send prompt that may result in file creation."""
        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        # Emit status
        await self._event_queue.put(FileEvent(type=EventType.SESSION_STATUS))

        # Parse prompt for file creation intent
        # In reality, the LLM would determine this
        if "create" in prompt.lower() and "file" in prompt.lower():
            # Extract target path from prompt or use default
            target_file = self.output_dir / "hello.py"

            # Simulate file creation
            file_content = '''"""Auto-generated file."""


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("World"))
'''

            # Create the file
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target_file.write_text(file_content)

            # Emit file diff event
            await self._event_queue.put(FileEvent(
                type=EventType.SESSION_DIFF,
                path=str(target_file),
                content=file_content,
            ))

        # Store messages
        self._sessions[session_id].append({"role": "user", "content": prompt})
        self._sessions[session_id].append({
            "role": "assistant",
            "content": f"Created file at {self.output_dir}",
        })

        await self._event_queue.put(FileEvent(type=EventType.MESSAGE_UPDATED))
        await self._event_queue.put(FileEvent(type=EventType.SESSION_IDLE))

    async def subscribe_events(self) -> AsyncIterator[FileEvent]:
        """Subscribe to events."""
        while True:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=60.0,
                )
                yield event
                if event.type == EventType.SESSION_IDLE:
                    break
            except asyncio.TimeoutError:
                break

    async def get_messages(self, session_id: str) -> list[dict]:
        """Get session messages."""
        return self._sessions.get(session_id, [])


@dataclass
class FileCreateResult:
    """Result of file creation operation."""
    success: bool
    file_path: str | None = None
    file_content: str | None = None
    response: str | None = None
    error: str | None = None


async def run_sdk_file_create() -> FileCreateResult:
    """
    Demonstrate file creation with agent SDK.
    """
    print("=" * 50)
    print("SDK File Creation POC")
    print("=" * 50)
    print(f"Provider: {PROVIDER}, Model: {MODEL}")
    print(f"Output dir: {OUTPUT_DIR}")
    print()

    # Clean output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = FileCreationClient(OUTPUT_DIR)

    # Create session
    session_id = await client.create_session("File Creation POC")
    print(f"Session created: {session_id}")

    # Prompt to create a file
    target_file = OUTPUT_DIR / "hello.py"
    prompt = f"""Create a simple Python file at {target_file} that:
1. Defines a function called greet(name) that returns "Hello, {{name}}!"
2. Has a main block that calls greet("World") and prints the result

Just create the file, nothing else."""

    print("Sending prompt to create file...")
    print(f"Target: {target_file}")
    print()

    # Stream events
    print("[STREAM] Waiting for events...")

    async def stream_events():
        async for event in client.subscribe_events():
            timestamp = "00:00:00"  # Simplified
            if event.type == EventType.SESSION_DIFF:
                print(f"[{timestamp}] FILE: {event.path}")
            elif event.type == EventType.SESSION_IDLE:
                print(f"[{timestamp}] Session complete (idle)")
            else:
                print(f"[{timestamp}] {event.type.value}")

    # Run concurrently
    await asyncio.gather(
        client.send_prompt(session_id, prompt, PROVIDER, MODEL),
        stream_events(),
    )

    # Get response
    messages = await client.get_messages(session_id)
    response = ""
    for msg in messages:
        if msg.get("role") == "assistant":
            response = msg.get("content", "")
            break

    print(f"Response: {response[:500]}")
    print()

    # Check if file was created
    print("Checking if file was created...")
    if target_file.exists():
        content = target_file.read_text()
        print("SUCCESS: File created!")
        print()
        print("File content:")
        print("-" * 40)
        print(content)
        print("-" * 40)

        return FileCreateResult(
            success=True,
            file_path=str(target_file),
            file_content=content,
            response=response,
        )
    else:
        print("File was NOT created at expected path.")
        files = list(OUTPUT_DIR.iterdir()) if OUTPUT_DIR.exists() else []
        print(f"Files in {OUTPUT_DIR}: {[f.name for f in files]}")

        return FileCreateResult(
            success=False,
            response=response,
            error="File was not created at expected path",
        )


# CLI runner
if __name__ == "__main__":
    async def main():
        result = await run_sdk_file_create()
        print()
        print("=" * 50)
        print("RESULT:", "SUCCESS" if result.success else "FAILED")
        if result.error:
            print("Error:", result.error)

        raise SystemExit(0 if result.success else 1)

    asyncio.run(main())
