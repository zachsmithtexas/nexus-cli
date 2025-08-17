"""Codex CLI provider."""

import asyncio
import subprocess

from .base import BaseProvider


class CodexCliProvider(BaseProvider):
    """Provider for Codex CLI."""

    def __init__(self, model_name: str, api_key: str | None = None):
        super().__init__(model_name, api_key)

    async def complete(self, prompt: str) -> str:
        """Complete a prompt using Codex CLI."""
        try:
            # Command format: ["codex", "chat", "--model", "${MODEL}", "--stdin"]
            process = await asyncio.create_subprocess_exec(
                "codex",
                "chat",
                "--model",
                self.model_name,
                "--stdin",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=prompt.encode())

            if process.returncode != 0:
                raise RuntimeError(f"Codex CLI failed: {stderr.decode()}")

            return stdout.decode().strip()

        except FileNotFoundError:
            raise RuntimeError("Codex CLI not found. Please install it first.")
        except Exception as e:
            raise RuntimeError(f"Codex CLI error: {e!s}")

    def is_available(self) -> bool:
        """Check if Codex CLI is available."""
        try:
            result = subprocess.run(
                ["codex", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
