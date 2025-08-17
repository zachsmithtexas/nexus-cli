"""Project Manager Agent - Scope tasks, set acceptance criteria, move to sprint."""

import asyncio
from pathlib import Path

from rich.console import Console

from core.config import ConfigManager
from core.queue import TaskQueue
from core.task import TaskStatus

console = Console()


class ProjectManagerAgent:
    """Agent responsible for task scoping and sprint planning."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)

    async def scope_task(self, task_id: str) -> bool:
        """Scope a task by adding acceptance criteria and details."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return False

        console.log(f"Scoping task: {task.title}")

        # Simple scoping logic - in real implementation would use AI
        if not task.acceptance_criteria:
            # Add basic acceptance criteria based on task type
            if "implement" in task.title.lower() or "create" in task.title.lower():
                task.acceptance_criteria = [
                    "Implementation is complete and functional",
                    "Code follows project coding standards",
                    "Unit tests are written and passing",
                    "Documentation is updated if needed",
                ]
            elif "fix" in task.title.lower() or "bug" in task.title.lower():
                task.acceptance_criteria = [
                    "Issue is identified and root cause found",
                    "Fix is implemented and tested",
                    "No regression issues introduced",
                    "Bug is verified as resolved",
                ]
            else:
                task.acceptance_criteria = [
                    "Requirements are clearly defined",
                    "Solution is implemented",
                    "Quality checks are performed",
                    "Deliverable meets expectations",
                ]

        # Set priority based on tags
        if "urgent" in task.tags or "critical" in task.tags:
            task.priority = "high"
        elif "enhancement" in task.tags or "nice-to-have" in task.tags:
            task.priority = "low"
        else:
            task.priority = "medium"

        # Assign to appropriate agent based on task type
        if any(
            keyword in task.description.lower()
            for keyword in ["implement", "code", "function", "class"]
        ):
            # Check complexity to decide senior vs junior
            if any(
                keyword in task.description.lower()
                for keyword in ["complex", "architecture", "design", "integration"]
            ):
                task.assigned_agent = "senior_dev"
            else:
                task.assigned_agent = "junior_dev"
        elif "test" in task.description.lower() or "qa" in task.description.lower():
            task.assigned_agent = "release_qa"
        else:
            task.assigned_agent = "senior_dev"  # Default for unclear tasks

        task.add_activity(
            "scoped by project manager",
            "project_manager",
            f"Added acceptance criteria, set priority to {task.priority}, assigned to {task.assigned_agent}",
        )

        # Update the task
        self.task_queue.update_task(task)

        console.log(
            f"Task {task_id} scoped - Priority: {task.priority}, Assigned: {task.assigned_agent}"
        )
        return True

    async def move_to_sprint(self, task_id: str) -> bool:
        """Move a scoped task to the sprint queue."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return False

        if task.status != TaskStatus.BACKLOG:
            console.log(
                f"Task {task_id} is not in backlog (current status: {task.status.value})"
            )
            return False

        if not task.acceptance_criteria:
            console.log(f"Task {task_id} needs to be scoped first")
            return False

        # Move to sprint
        self.task_queue.move_task(
            task_id,
            TaskStatus.SPRINT,
            "project_manager",
            "Moved to sprint - ready for development",
        )

        console.log(f"Task {task_id} moved to sprint")
        return True

    async def plan_sprint(self, max_tasks: int = 5) -> list[str]:
        """Plan a sprint by selecting and moving tasks from backlog."""
        backlog_tasks = self.task_queue.list_tasks(TaskStatus.BACKLOG)
        sprint_tasks = self.task_queue.list_tasks(TaskStatus.SPRINT)

        # Don't exceed max tasks in sprint
        available_slots = max_tasks - len(sprint_tasks)
        if available_slots <= 0:
            console.log("Sprint is already full")
            return []

        # Sort backlog by priority (high > medium > low)
        priority_order = {"high": 3, "medium": 2, "low": 1}
        backlog_tasks.sort(
            key=lambda t: priority_order.get(t.priority, 0), reverse=True
        )

        moved_tasks = []
        for task in backlog_tasks[:available_slots]:
            # Scope task if not already scoped
            if not task.acceptance_criteria:
                await self.scope_task(task.id)

            # Move to sprint
            if await self.move_to_sprint(task.id):
                moved_tasks.append(task.id)

        console.log(f"Planned sprint with {len(moved_tasks)} tasks: {moved_tasks}")
        return moved_tasks

    async def get_backlog_summary(self) -> str:
        """Get a summary of the current backlog."""
        backlog_tasks = self.task_queue.list_tasks(TaskStatus.BACKLOG)

        if not backlog_tasks:
            return "Backlog is empty."

        summary_lines = [f"Backlog Summary ({len(backlog_tasks)} tasks):"]

        # Group by priority
        by_priority = {}
        for task in backlog_tasks:
            priority = task.priority
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(task)

        for priority in ["high", "medium", "low"]:
            if priority in by_priority:
                summary_lines.append(f"\n{priority.upper()} Priority:")
                for task in by_priority[priority]:
                    status = (
                        "✓ Scoped" if task.acceptance_criteria else "○ Needs scoping"
                    )
                    summary_lines.append(f"  - {task.title} ({task.id}) - {status}")

        return "\n".join(summary_lines)


async def main():
    """Main entry point for project manager agent."""
    import sys

    if len(sys.argv) < 2:
        console.log("Usage: python -m agents.project_manager.main <command>")
        return

    base_path = Path.cwd()
    agent = ProjectManagerAgent(base_path)

    command = sys.argv[1]

    if command == "scope_task" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        success = await agent.scope_task(task_id)
        console.log(f"Scoping {'successful' if success else 'failed'}")

    elif command == "move_to_sprint" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        success = await agent.move_to_sprint(task_id)
        console.log(f"Sprint move {'successful' if success else 'failed'}")

    elif command == "plan_sprint":
        max_tasks = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        moved_tasks = await agent.plan_sprint(max_tasks)
        console.log(f"Sprint planned with tasks: {moved_tasks}")

    elif command == "backlog_summary":
        summary = await agent.get_backlog_summary()
        console.log(summary)

    else:
        console.log("Unknown command or missing arguments")


if __name__ == "__main__":
    asyncio.run(main())
