"""Discord integration for Nexus CLI.

Avoid importing the bot module at package import time to prevent runpy warnings
when running `python -m connectors.discord.bot`. Provide a lazy proxy instead.
"""

def start_bot(*args, **kwargs):  # pragma: no cover - thin import proxy
    from .bot import start_bot as _start_bot
    return _start_bot(*args, **kwargs)

__all__ = ["start_bot"]
