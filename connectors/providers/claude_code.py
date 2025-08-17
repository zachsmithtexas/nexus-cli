"""Claude Code CLI provider."""

import asyncio
import subprocess

from .base import BaseProvider


class ClaudeCodeProvider(BaseProvider):
    """Provider for Claude Code CLI."""

    def __init__(self, model_name: str, api_key: str | None = None):
        super().__init__(model_name, api_key)

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using Claude Code CLI."""
        try:
            # Command format: ["claude", "--model", "${MODEL}"]
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--model",
                self.model_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=prompt.encode())

            if process.returncode != 0:
                raise RuntimeError(f"Claude Code CLI failed: {stderr.decode()}")

            return stdout.decode().strip()

        except FileNotFoundError:
            raise RuntimeError("Claude Code CLI not found. Please install it first.")
        except Exception as e:
            raise RuntimeError(f"Claude Code CLI error: {e!s}")

    def is_available(self) -> bool:
        """Check if Claude Code CLI is available."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
