"""Main orchestrator for file watching and task routing."""

from dotenv import load_dotenv, find_dotenv

# Load environment from .env in CWD and optional .env.local
_ = load_dotenv(find_dotenv(usecwd=True), override=False)
_ = load_dotenv(".env.local", override=False)

import asyncio
import os
from pathlib import Path

from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import ConfigManager
from .queue import TaskQueue
from .router import ProviderRouter
from .task import Task, TaskStatus
import os
import httpx

console = Console()


def _mask(value: object | None) -> str:
    """Mask sensitive values for logging."""
    if value is None:
        return "Not configured"
    s = str(value)
    if not s:
        return "Not configured"
    return (s[:4] + "…" + s[-4:]) if len(s) > 8 else "****"


class TaskFileHandler(FileSystemEventHandler):
    """Handles file system events for task files."""

    def __init__(self, orchestrator: "Orchestrator"):
        self.orchestrator = orchestrator

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith(".md"):
            loop = getattr(self.orchestrator, "loop", None)
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.orchestrator.process_new_task(Path(event.src_path)), loop
                )
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(
                        asyncio.create_task,
                        self.orchestrator.process_new_task(Path(event.src_path)),
                    )
                except RuntimeError:
                    # As a last resort, run synchronously in this thread
                    asyncio.run(
                        self.orchestrator.process_new_task(Path(event.src_path))
                    )

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith(".md"):
            loop = getattr(self.orchestrator, "loop", None)
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.orchestrator.process_task_update(Path(event.src_path)), loop
                )
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(
                        asyncio.create_task,
                        self.orchestrator.process_task_update(Path(event.src_path)),
                    )
                except RuntimeError:
                    asyncio.run(
                        self.orchestrator.process_task_update(Path(event.src_path))
                    )


class Orchestrator:
    """Main orchestrator for the Nexus CLI system."""

    def __init__(self, base_path: Path, loop: asyncio.AbstractEventLoop | None = None):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)
        self.router = ProviderRouter(self.config_manager)
        self.observer: Observer | None = None
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = loop
        self._log_startup_config()

    def _log_startup_config(self) -> None:
        """Log masked orchestrator configuration and provider status."""
        settings = self.config_manager.get_settings()
        console.log("⚙️ Orchestrator Configuration:")
        console.log(f"  Project: {settings.project_name}")
        console.log(f"  Log Level: {settings.log_level}")
        console.log(f"  Obsidian: {settings.obsidian_path or 'Not configured'}")
        providers = self.router.get_available_providers()
        console.log(f"  Providers available: {len(providers)}")
        # Masked provider API keys presence
        provider_keys = [
            "DEEPSEEK_API_KEY",
            "OPENROUTER_API_KEY",
            "QWEN_API_KEY",
        ]
        masked = [f"{k}={_mask(os.getenv(k))}" for k in provider_keys if os.getenv(k)]
        console.log(f"  Provider Keys: {', '.join(masked) or 'None'}")

    async def start(self):
        """Start the orchestrator."""
        console.log("Starting Nexus CLI Orchestrator...")
        # Capture running loop for thread-safe scheduling from watchdog threads
        if self.loop is None:
            self.loop = asyncio.get_running_loop()

        # Set up file watching
        self.observer = Observer()
        handler = TaskFileHandler(self)

        # Watch inbox directory for new tasks
        inbox_path = self.base_path / "tasks" / "inbox"
        self.observer.schedule(handler, str(inbox_path), recursive=False)

        self.observer.start()
        self.running = True

        console.log("Orchestrator started. Watching for tasks...")

        # Process any existing tasks in inbox
        await self.process_existing_inbox_tasks()

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()

    async def stop(self):
        """Stop the orchestrator."""
        console.log("Stopping orchestrator...")
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

    async def process_existing_inbox_tasks(self):
        """Process any existing tasks in the inbox."""
        inbox_tasks = self.task_queue.list_tasks(TaskStatus.INBOX)
        for task in inbox_tasks:
            await self.process_task_promotion(task)

    async def process_new_task(self, file_path: Path):
        """Process a newly created task file."""
        try:
            if file_path.parent.name == "inbox":
                with open(file_path) as f:
                    content = f.read()

                task = Task.from_markdown(content)
                await self.process_task_promotion(task)

        except Exception as e:
            console.log(f"Error processing new task {file_path}: {e}")

    async def process_task_update(self, file_path: Path):
        """Process updates to existing task files."""
        try:
            # For now, just log the update
            console.log(f"Task updated: {file_path.name}")
        except Exception as e:
            console.log(f"Error processing task update {file_path}: {e}")

    async def process_task_promotion(self, task: Task):
        """Process task promotion from inbox to backlog."""
        try:
            console.log(f"Processing task promotion: {task.title}")

            # Normalize the task with front matter
            if task.status == TaskStatus.INBOX:
                # Move to backlog and add activity
                self.task_queue.move_task(
                    task.id,
                    TaskStatus.BACKLOG,
                    "orchestrator",
                    "Auto-promoted from inbox with normalized front matter",
                )

                # Process pipeline of roles (each runs once per task)
                # Allow overriding pipeline via env (comma-separated roles)
                roles_env = os.getenv(
                    "ORCHESTRATOR_ROLES",
                    "communications,project_manager,senior_dev,junior_dev,release_qa",
                )
                roles = [r.strip() for r in roles_env.split(",") if r.strip()]
                default_instructions = {
                    "communications": "Review the idea and create/normalize the task card, updating the roadmap if needed.",
                    "project_manager": "Triage and scope this task. Add or refine acceptance criteria and move it through planning.",
                    "senior_dev": "Assess complexity, outline the approach, and create any necessary subtasks.",
                    "junior_dev": "Implement the next actionable step or utility according to the plan.",
                    "release_qa": "Add validation steps and ensure release notes are updated if changes are user-facing.",
                }
                pipeline: list[tuple[str, str]] = [
                    (role, default_instructions.get(role, "Proceed with your responsibilities for this task."))
                    for role in roles
                ]
                    (
                        "communications",
                        "Review the idea and create/normalize the task card, updating the roadmap if needed.",
                    ),
                    (
                        "project_manager",
                        "Triage and scope this task. Add or refine acceptance criteria and move it through planning.",
                    ),
                    (
                        "senior_dev",
                        "Assess complexity, outline the approach, and create any necessary subtasks.",
                    ),
                    (
                        "junior_dev",
                        "Implement the next actionable step or utility according to the plan.",
                    ),
                    (
                        "release_qa",
                        "Add validation steps and ensure release notes are updated if changes are user-facing.",
                    ),
                ]

                for role, instruction in pipeline:
                    # Skip roles already processed for this task
                    if any(
                        a.agent == role and a.action.startswith("processed by")
                        for a in task.activity
                    ):
                        continue
                    await self.route_to_agent(role, task, instruction)

        except Exception as e:
            console.log(f"Error promoting task {task.id}: {e}")

    async def route_to_agent(
        self, role: str, task: Task, instruction: str
    ) -> str | None:
        """Route a task to a specific agent role."""
        try:
            prompt = f"""
Task: {task.title}
Description: {task.description}
Current Status: {task.status.value}

Instruction: {instruction}

Please process this task according to your role as {role}.
"""

            result = await self.router.complete(role, prompt)

            if result:
                # Add activity entry
                task.add_activity(
                    f"processed by {role}",
                    role,
                    result[:100] + "..." if len(result) > 100 else result,
                )
                # Ensure tasks remain in backlog after processing
                if task.status == TaskStatus.INBOX:
                    task.status = TaskStatus.BACKLOG
                self.task_queue.update_task(task)

                console.log(f"Task {task.id} processed by {role}")
                # Post an update to Discord via webhook if configured
                await self._post_discord_webhook(role, f"Task `{task.id}` processed by {role}: {task.title}")
                return result
            else:
                console.log(f"Failed to get response from {role} for task {task.id}")
                return None

        except Exception as e:
            console.log(f"Error routing task {task.id} to {role}: {e}")
            return None

    async def _post_discord_webhook(self, agent: str, content: str) -> None:
        """Post an update to the configured Discord webhook for the agent.

        This does not require the bot; it uses the webhook URLs from settings.
        """
        try:
            settings = self.config_manager.get_settings()
            webhook_url = (settings.discord.webhooks or {}).get(agent)
            if not webhook_url or webhook_url.startswith("${"):
                return
            # Display names and avatar URLs can be overridden per message
            agent_names = {
                "communications": "Communications Agent",
                "project_manager": "Project Manager",
                "senior_dev": "Senior Developer",
                "junior_dev": "Junior Developer",
                "release_qa": "Release QA",
            }
            avatar_env = {
                "communications": os.getenv("COMMUNICATIONS_WEBHOOK_AVATAR"),
                "project_manager": os.getenv("PM_WEBHOOK_AVATAR"),
                "senior_dev": os.getenv("SD_WEBHOOK_AVATAR"),
                "junior_dev": os.getenv("JD_WEBHOOK_AVATAR"),
                "release_qa": os.getenv("RQE_WEBHOOK_AVATAR"),
            }
            payload = {
                "content": content[:2000],
                "username": agent_names.get(agent, agent.replace("_", " ").title()),
            }
            if avatar_env.get(agent):
                payload["avatar_url"] = avatar_env[agent]
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(webhook_url, json=payload)
        except Exception as e:
            console.log(f"Webhook post failed for {agent}: {e}")

    def get_status(self) -> dict:
        """Get current system status."""
        queue_counts = self.task_queue.get_queue_counts()
        available_providers = self.router.get_available_providers()

        return {
            "running": self.running,
            "queue_counts": queue_counts,
            "available_providers": available_providers,
            "total_tasks": sum(queue_counts.values()),
        }
