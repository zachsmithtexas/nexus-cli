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
            asyncio.create_task(
                self.orchestrator.process_new_task(Path(event.src_path))
            )

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith(".md"):
            asyncio.create_task(
                self.orchestrator.process_task_update(Path(event.src_path))
            )


class Orchestrator:
    """Main orchestrator for the Nexus CLI system."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)
        self.router = ProviderRouter(self.config_manager)
        self.observer: Observer | None = None
        self.running = False
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

                # Route to communications agent for initial processing
                await self.route_to_agent(
                    "communications",
                    task,
                    "Please review this task and update the roadmap if needed.",
                )

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
                self.task_queue.update_task(task)

                console.log(f"Task {task.id} processed by {role}")
                return result
            else:
                console.log(f"Failed to get response from {role} for task {task.id}")
                return None

        except Exception as e:
            console.log(f"Error routing task {task.id} to {role}: {e}")
            return None

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
