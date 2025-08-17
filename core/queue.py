"""File-backed task queue implementation."""

from pathlib import Path

from rich.console import Console

from .task import Task, TaskStatus

console = Console()


class TaskQueue:
    """File-backed task queue manager."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.queues = {
            TaskStatus.INBOX: self.base_path / "tasks" / "inbox",
            TaskStatus.BACKLOG: self.base_path / "tasks" / "backlog",
            TaskStatus.SPRINT: self.base_path / "tasks" / "sprint",
            TaskStatus.DONE: self.base_path / "tasks" / "done",
        }

        # Ensure directories exist
        for queue_dir in self.queues.values():
            queue_dir.mkdir(parents=True, exist_ok=True)

    def add_task(self, task: Task, status: TaskStatus | None = None) -> Path:
        """Add a task to the specified queue."""
        if status:
            task.status = status

        queue_dir = self.queues[task.status]
        filename = f"{task.id}_{task.title.lower().replace(' ', '_')}.md"
        file_path = queue_dir / filename

        with open(file_path, "w") as f:
            f.write(task.to_markdown())

        console.log(f"Added task {task.id} to {task.status.value}")
        return file_path

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID from any queue."""
        for status, queue_dir in self.queues.items():
            for file_path in queue_dir.glob(f"{task_id}_*.md"):
                return self._load_task_from_file(file_path)
        return None

    def list_tasks(self, status: TaskStatus) -> list[Task]:
        """List all tasks in a specific queue."""
        tasks = []
        queue_dir = self.queues[status]

        for file_path in queue_dir.glob("*.md"):
            try:
                task = self._load_task_from_file(file_path)
                if task:
                    tasks.append(task)
            except Exception as e:
                console.log(f"Error loading task from {file_path}: {e}")

        return sorted(tasks, key=lambda t: t.created_at)

    def move_task(
        self,
        task_id: str,
        new_status: TaskStatus,
        agent: str,
        details: str | None = None,
    ) -> Task | None:
        """Move a task to a different queue."""
        task = self.get_task(task_id)
        if not task:
            return None

        # Remove from current queue
        old_file = self._find_task_file(task_id)
        if old_file:
            old_file.unlink()

        # Update task status and add activity
        old_status = task.status
        task.status = new_status
        task.add_activity(
            f"moved from {old_status.value} to {new_status.value}", agent, details
        )

        # Add to new queue
        self.add_task(task, new_status)

        console.log(
            f"Moved task {task_id} from {old_status.value} to {new_status.value}"
        )
        return task

    def update_task(self, task: Task) -> Path:
        """Update an existing task."""
        # Remove old file
        old_file = self._find_task_file(task.id)
        if old_file:
            old_file.unlink()

        # Save updated task
        return self.add_task(task)

    def _load_task_from_file(self, file_path: Path) -> Task | None:
        """Load a task from a markdown file."""
        try:
            with open(file_path) as f:
                content = f.read()
            return Task.from_markdown(content)
        except Exception as e:
            console.log(f"Error loading task from {file_path}: {e}")
            return None

    def _find_task_file(self, task_id: str) -> Path | None:
        """Find the file containing a specific task."""
        for queue_dir in self.queues.values():
            for file_path in queue_dir.glob(f"{task_id}_*.md"):
                return file_path
        return None

    def get_queue_counts(self) -> dict:
        """Get count of tasks in each queue."""
        counts = {}
        for status, queue_dir in self.queues.items():
            counts[status.value] = len(list(queue_dir.glob("*.md")))
        return counts
