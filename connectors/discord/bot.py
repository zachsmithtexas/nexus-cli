"""Discord bot integration for Nexus CLI with agent personas."""

from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env in CWD and optional .env.local overlay
_ = load_dotenv(find_dotenv(usecwd=True), override=False)
_ = load_dotenv(".env.local", override=False)

import asyncio
import os
from pathlib import Path

import discord
import httpx
from discord.ext import commands
from discord import app_commands
from rich.console import Console

from agents.communications.main import CommunicationsAgent
from core.config import ConfigManager
from core.orchestrator import Orchestrator
from core.queue import TaskQueue

console = Console()


def _mask(value: object | None) -> str:
    """Mask sensitive or identifier-like values for safer logging."""
    if value is None:
        return "Not configured"
    s = str(value)
    if not s:
        return "Not configured"
    return (s[:4] + "…" + s[-4:]) if len(s) > 8 else "****"


def resolve_id_or_name(value: str) -> int | None:
    """Resolve a Discord ID from numeric string or channel/guild name."""
    if not value or value.startswith("${"):
        return None

    # Try to parse as integer
    try:
        return int(value)
    except ValueError:
        # For now, just return None for name-based resolution
        # In a real implementation, this would resolve names to IDs
        return None


class NexusBot(commands.Bot):
    """Discord bot for Nexus CLI task management with agent personas."""

    def __init__(self, base_path: Path):
        # Optional privileged intents via env (default OFF)
        use_msg_content = os.getenv("DISCORD_MESSAGE_CONTENT", "0").lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        use_members = os.getenv("DISCORD_MEMBERS", "0").lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        use_presence = os.getenv("DISCORD_PRESENCE", "0").lower() in (
            "1",
            "true",
            "yes",
            "y",
        )

        # Set up minimal intents for slash commands; toggle privileged ones via env
        intents = discord.Intents.default()
        intents.guilds = True
        intents.dm_messages = True
        intents.message_content = use_msg_content  # privileged
        intents.members = use_members              # privileged
        intents.presences = use_presence           # privileged

        super().__init__(command_prefix="!", intents=intents)

        console.log(
            f"[Discord Intents] guilds={intents.guilds} msg_content={intents.message_content} "
            f"members={intents.members} presences={intents.presences}"
        )

        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)
        self.communications_agent = CommunicationsAgent(self.base_path)
        self.orchestrator: Orchestrator | None = None

        # Discord configuration
        self.settings = self.config_manager.get_settings()
        self.discord_config = self.settings.discord

        # Resolve IDs
        self.guild_id = resolve_id_or_name(self.discord_config.guild_id or "")
        self.commands_channel_id = resolve_id_or_name(
            self.discord_config.commands_channel_id or ""
        )
        self.updates_channel_id = resolve_id_or_name(
            self.discord_config.updates_channel_id or ""
        )

        # Webhook URLs for agent personas
        self.webhooks: dict[str, str] = {}
        for agent, url in self.discord_config.webhooks.items():
            if url and not url.startswith("${"):
                self.webhooks[agent] = url

        self._log_startup_config()

    def _log_startup_config(self):
        """Log configuration at startup (redacting sensitive info)."""
        console.log("🤖 Discord Bot Configuration:")
        console.log(f"  Guild ID: {_mask(self.guild_id)}")
        console.log(f"  Commands Channel: {_mask(self.commands_channel_id)}")
        console.log(f"  Updates Channel: {_mask(self.updates_channel_id)}")
        console.log(
            f"  Agent Webhooks: {list(self.webhooks.keys()) or 'None'}"
        )
        token = self.discord_config.bot_token
        console.log(f"  Bot Token: {_mask(token) if token and not token.startswith('${') else 'Not configured'}")

    async def setup_hook(self):
        """Set up bot, register commands, and sync to guild if configured."""
        console.log("Setting up Nexus Discord Bot...")

        # Register slash commands before syncing
        try:
            self.tree.add_command(idea_command)
            self.tree.add_command(feedback_command)
            self.tree.add_command(status_command)
        except Exception as e:
            console.log(f"While adding commands: {e}")

        # Sync application commands
        if self.guild_id:
            try:
                guild = discord.Object(id=self.guild_id)
                try:
                    # Ensure any global commands are copied if present
                    self.tree.copy_global_to(guild=guild)
                except Exception:
                    pass
                synced = await self.tree.sync(guild=guild)
                console.log(f"Synced {len(synced)} commands to guild {self.guild_id}")
            except Exception as e:
                console.log(f"Failed to sync commands to guild: {e}")
        else:
            try:
                synced = await self.tree.sync()
                console.log(f"Synced {len(synced)} global commands")
            except Exception as e:
                console.log(f"Failed to sync global commands: {e}")

        # Start the orchestrator in background
        self.orchestrator = Orchestrator(self.base_path)
        asyncio.create_task(self.orchestrator.start())

        console.log("Nexus Discord Bot ready!")

    async def on_ready(self):
        """Called when the bot is ready."""
        console.log(f"{self.user} has connected to Discord!")
        console.log(f"Bot is in {len(self.guilds)} guilds")

        # Command sync handled in setup_hook
        if not self.guild_id:
            console.log("No guild_id configured; commands synced globally in setup.")

    def _is_valid_request(self, interaction: discord.Interaction) -> bool:
        """Check if request is from correct guild and channel."""
        # Check guild
        if self.guild_id and interaction.guild_id != self.guild_id:
            return False

        # Check channel for commands
        if (
            self.commands_channel_id
            and interaction.channel_id != self.commands_channel_id
        ):
            return False

        return True

    async def post_agent_update(
        self, agent: str, content: str, files: list[Path] | None = None
    ):
        """Post an update as an agent persona."""
        if not content.strip():
            return

        # Try webhook first
        webhook_url = self.webhooks.get(agent)
        if webhook_url:
            try:
                await self._post_via_webhook(webhook_url, agent, content, files)
                return
            except Exception as e:
                console.log(
                    f"Webhook post failed for {agent}: {e}, falling back to bot message"
                )

        # Fallback to bot message in updates channel
        await self._post_via_bot(agent, content, files)

    async def _post_via_webhook(
        self,
        webhook_url: str,
        agent: str,
        content: str,
        files: list[Path] | None = None,
    ):
        """Post message via webhook with agent persona."""
        agent_names = {
            "communications": "Communications Agent",
            "project_manager": "Project Manager",
            "senior_dev": "Senior Developer",
            "junior_dev": "Junior Developer",
            "release_qa": "Release QA",
        }

        agent_avatars = {
            "communications": "📢",
            "project_manager": "📋",
            "senior_dev": "👨‍💻",
            "junior_dev": "👩‍💻",
            "release_qa": "🔍",
        }

        username = agent_names.get(agent, agent.replace("_", " ").title())
        avatar_url = None  # Could be set to actual avatar URLs

        payload = {
            "content": content[:2000],  # Discord limit
            "username": username,
        }

        if avatar_url:
            payload["avatar_url"] = avatar_url

        async with httpx.AsyncClient() as client:
            if files:
                # Handle file uploads (simplified)
                response = await client.post(webhook_url, json=payload)
            else:
                response = await client.post(webhook_url, json=payload)

            response.raise_for_status()

    async def _post_via_bot(
        self, agent: str, content: str, files: list[Path] | None = None
    ):
        """Post message via bot with agent prefix."""
        if not self.updates_channel_id:
            console.log(f"No updates channel configured, cannot post {agent} update")
            return

        channel = self.get_channel(self.updates_channel_id)
        if not channel:
            console.log(f"Updates channel {self.updates_channel_id} not found")
            return

        agent_emojis = {
            "communications": "📢",
            "project_manager": "📋",
            "senior_dev": "👨‍💻",
            "junior_dev": "👩‍💻",
            "release_qa": "🔍",
        }

        emoji = agent_emojis.get(agent, "🤖")
        agent_name = agent.replace("_", " ").title()

        prefixed_content = f"{emoji} **[{agent_name}]** {content}"

        # Split long messages
        if len(prefixed_content) > 2000:
            prefixed_content = prefixed_content[:1997] + "..."

        try:
            await channel.send(prefixed_content)
        except Exception as e:
            console.log(f"Failed to send bot message: {e}")


# Global bot instance
bot = None


def get_bot(base_path: Path) -> NexusBot:
    """Get or create the bot instance."""
    global bot
    if bot is None:
        bot = NexusBot(base_path)
    return bot


@discord.app_commands.command(
    name="idea", description="Submit a new idea for development"
)
async def idea_command(interaction: discord.Interaction, text: str):
    """Handle /idea command - create a task from user idea."""
    try:
        # Get bot instance and validate request
        bot_instance = get_bot(Path.cwd())

        if not bot_instance._is_valid_request(interaction):
            await interaction.response.send_message(
                "❌ This command can only be used in the configured server and channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        console.log(f"Received idea from {interaction.user}: {text[:50]}...")

        # Process the idea through communications agent
        task = await bot_instance.communications_agent.process_idea(text)

        # Send ephemeral response
        await interaction.followup.send(
            f"💡 **Idea captured!** Created task `{task.id}` - {task.title}",
            ephemeral=True,
        )

        # Post update to updates channel via agent
        await bot_instance.post_agent_update(
            "communications",
            f"New idea received: **{task.title}** (Task ID: `{task.id}`)",
        )

        console.log(f"Idea processed successfully: {task.id}")

    except Exception as e:
        console.log(f"Error processing idea: {e}")
        await interaction.followup.send(
            f"❌ Sorry, there was an error processing your idea: {e!s}", ephemeral=True
        )


@discord.app_commands.command(
    name="feedback", description="Submit feedback about the system"
)
async def feedback_command(interaction: discord.Interaction, text: str):
    """Handle /feedback command - process user feedback."""
    try:
        # Get bot instance and validate request
        bot_instance = get_bot(Path.cwd())

        if not bot_instance._is_valid_request(interaction):
            await interaction.response.send_message(
                "❌ This command can only be used in the configured server and channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        console.log(f"Received feedback from {interaction.user}: {text[:50]}...")

        # Save feedback to vault/inbox/feedback
        feedback_dir = bot_instance.base_path / "vault" / "inbox" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        feedback_file = feedback_dir / f"feedback_{timestamp}.md"

        feedback_content = f"""---
user: {interaction.user.name}
user_id: {interaction.user.id}
timestamp: {datetime.now().isoformat()}
---

# User Feedback

{text}
"""

        with open(feedback_file, "w") as f:
            f.write(feedback_content)

        # Also process through communications agent if significant
        task = await bot_instance.communications_agent.process_feedback(text)

        # Send ephemeral response
        response_text = "📝 **Feedback received!** Thank you for your input."
        if task:
            response_text += f" Created task `{task.id}` to address it."

        await interaction.followup.send(response_text, ephemeral=True)

        console.log("Feedback processed successfully")

    except Exception as e:
        console.log(f"Error processing feedback: {e}")
        await interaction.followup.send(
            f"❌ Sorry, there was an error processing your feedback: {e!s}",
            ephemeral=True,
        )


@discord.app_commands.command(name="status", description="Get current system status")
async def status_command(interaction: discord.Interaction):
    """Handle /status command - show system status."""
    try:
        # Get bot instance and validate request
        bot_instance = get_bot(Path.cwd())

        if not bot_instance._is_valid_request(interaction):
            await interaction.response.send_message(
                "❌ This command can only be used in the configured server and channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        console.log(f"Status requested by {interaction.user}")

        # Get queue counts
        queue_counts = bot_instance.task_queue.get_queue_counts()

        # Get orchestrator status if available
        orchestrator_status = {}
        if bot_instance.orchestrator:
            orchestrator_status = bot_instance.orchestrator.get_status()

        # Create status message
        status_lines = ["📊 **Nexus CLI System Status**", "", "📋 **Task Queues:**"]

        total_tasks = sum(queue_counts.values())
        queue_icons = {"inbox": "📥", "backlog": "📋", "sprint": "🏃", "done": "✅"}

        for status, count in queue_counts.items():
            icon = queue_icons.get(status, "📄")
            status_lines.append(f"  {icon} {status.title()}: **{count}**")

        status_lines.append(f"  📊 Total: **{total_tasks}** tasks")

        # Orchestrator status
        if orchestrator_status:
            running = orchestrator_status.get("running", False)
            status_lines.extend(
                [
                    "",
                    f"⚙️ **Orchestrator:** {'🟢 Running' if running else '🔴 Stopped'}",
                    f"🔌 **Providers:** {len(orchestrator_status.get('available_providers', []))} available",
                ]
            )

        status_message = "\n".join(status_lines)

        await interaction.followup.send(status_message, ephemeral=True)
        console.log("Status command completed successfully")

    except Exception as e:
        console.log(f"Error getting status: {e}")
        await interaction.followup.send(
            f"❌ Sorry, there was an error getting the system status: {e!s}",
            ephemeral=True,
        )


async def start_bot(base_path: Path):
    """Start the Discord bot."""
    # Get bot instance
    bot_instance = get_bot(base_path)

    # Commands are added in setup_hook prior to syncing

    # Get Discord token
    token = bot_instance.discord_config.bot_token

    if not token or token.startswith("${"):
        raise SystemExit(
            "❌ DISCORD_BOT_TOKEN missing. Ensure .env is present or export the variable."
        )

    try:
        console.log("🤖 Starting Discord bot...")
        await bot_instance.start(token)
    except discord.LoginFailure:
        console.log("❌ Failed to login to Discord. Check your token.")
    except Exception as e:
        msg = str(e)
        if "privileged intents" in msg.lower():
            console.log(
                "⚠️ Privileged intents requested but not enabled. "
                "Disable via DISCORD_MESSAGE_CONTENT/DISCORD_MEMBERS/DISCORD_PRESENCE=0, "
                "or enable them in the Discord Dev Portal → Bot → Privileged Gateway Intents."
            )
        console.log(f"❌ Bot error: {e}")


async def main():
    """Main entry point for Discord bot."""
    import sys

    base_path = Path.cwd()

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - just verify setup
        console.log("Testing Discord bot setup...")

        config_manager = ConfigManager(base_path / "config")
        settings = config_manager.get_settings()
        discord_config = settings.discord

        console.log(
            f"Bot Token: {'✅ Configured' if discord_config.bot_token and not discord_config.bot_token.startswith('${') else '❌ Not configured'}"
        )
        console.log(
            f"Guild ID: {'✅ Configured' if discord_config.guild_id and not discord_config.guild_id.startswith('${') else '❌ Not configured'}"
        )
        console.log(
            f"Channels: {'✅ Configured' if discord_config.commands_channel_id and discord_config.updates_channel_id else '❌ Not fully configured'}"
        )
        console.log(
            f"Webhooks: {len([url for url in discord_config.webhooks.values() if url and not url.startswith('${')])}/{len(discord_config.webhooks)} configured"
        )

        console.log("Discord bot test complete")
        return

    # Start the bot
    await start_bot(base_path)


if __name__ == "__main__":
    asyncio.run(main())
