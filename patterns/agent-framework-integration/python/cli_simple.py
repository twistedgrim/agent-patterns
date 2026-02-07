"""
CLI Integration Pattern - Python Implementation

Uses subprocess to shell out to a coding agent CLI.
This is the simplest integration approach.
"""

import asyncio
import os
import tempfile
from pathlib import Path

MODEL = os.environ.get("AGENT_MODEL", "anthropic/claude-3-opus")


async def run_cli_simple(prompt: str) -> tuple[str, str]:
    """
    Run a coding agent via CLI.

    Writes prompt to temp file to avoid shell escaping issues,
    then pipes to the agent CLI.
    """
    # Write prompt to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        # Use asyncio subprocess for non-blocking execution
        # Replace 'agent-cli' with actual CLI (aider, etc.)
        proc = await asyncio.create_subprocess_shell(
            f'cat "{prompt_file}" | agent-cli run --model {MODEL}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=300.0,  # 5 minute timeout
        )

        return stdout.decode(), stderr.decode()
    finally:
        Path(prompt_file).unlink(missing_ok=True)


async def run_cli_with_streaming(
    prompt: str,
    on_chunk: callable | None = None,
) -> str:
    """
    Run CLI with streaming output.

    Reads stdout line by line for real-time feedback.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        proc = await asyncio.create_subprocess_shell(
            f'cat "{prompt_file}" | agent-cli run --model {MODEL}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        output_lines = []

        # Stream stdout
        async for line in proc.stdout:
            decoded = line.decode()
            output_lines.append(decoded)
            if on_chunk:
                on_chunk(decoded)

        await proc.wait()
        return "".join(output_lines)
    finally:
        Path(prompt_file).unlink(missing_ok=True)


# CLI runner
if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello"

    print("=" * 50)
    print("CLI Simple POC")
    print("=" * 50)
    print(f"Model: {MODEL}")
    print(f"Prompt: {prompt[:100]}...")
    print()

    async def main():
        stdout, stderr = await run_cli_simple(prompt)
        print("\n=== STDOUT ===")
        print(stdout)
        if stderr:
            print("\n=== STDERR ===")
            print(stderr)

    asyncio.run(main())
