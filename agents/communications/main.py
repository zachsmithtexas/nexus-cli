"""Communications Agent - Convert ideas/feedback into task cards and update roadmap."""

import asyncio
from pathlib import Path

from rich.console import Console

from core.config import ConfigManager
from core.queue import TaskQueue
from core.task import Task, TaskStatus

console = Console()


class CommunicationsAgent:
    """Agent responsible for converting ideas/feedback into structured task cards."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)
        self.roadmap_path = self.base_path / "docs" / "ROADMAP.md"

    async def process_idea(self, idea_text: str) -> Task:
        """Convert an idea into a structured task card."""
        console.log(f"Processing idea: {idea_text[:50]}...")

        # Create a basic task from the idea
        # In a real implementation, this would use AI to structure the idea
        lines = idea_text.strip().split("\n")
        title = lines[0] if lines else "New Idea"
        description = "\n".join(lines[1:]) if len(lines) > 1 else idea_text

        task = Task(
            title=title, description=description, status=TaskStatus.INBOX, tags=["idea"]
        )

        task.add_activity(
            "created from idea", "communications", "Converted user idea into task card"
        )

        # Save to inbox
        self.task_queue.add_task(task)

        # Update roadmap
        await self.update_roadmap(task)

        console.log(f"Created task {task.id} from idea")
        return task

    async def process_feedback(self, feedback_text: str) -> Task | None:
        """Process feedback and potentially create improvement tasks."""
        console.log(f"Processing feedback: {feedback_text[:50]}...")

        # For demo purposes, create a task for significant feedback
        if len(feedback_text.strip()) > 20:
            task = Task(
                title=f"Address feedback: {feedback_text[:30]}...",
                description=f"User feedback received:\n\n{feedback_text}",
                status=TaskStatus.INBOX,
                tags=["feedback", "improvement"],
            )

            task.add_activity(
                "created from feedback",
                "communications",
                "Converted user feedback into improvement task",
            )

            # Save to inbox
            self.task_queue.add_task(task)

            console.log(f"Created task {task.id} from feedback")
            return task

        return None

    async def update_roadmap(self, task: Task):
        """Update the roadmap with new task information."""
        try:
            # Ensure docs directory exists
            self.roadmap_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing roadmap or create new one
            if self.roadmap_path.exists():
                with open(self.roadmap_path) as f:
                    roadmap_content = f.read()
            else:
                roadmap_content = (
                    "# Project Roadmap\n\n## Upcoming Features\n\n## Recent Ideas\n\n"
                )

            # Add new task to recent ideas section
            task_entry = f"- **{task.title}** ({task.id}): {task.description[:100]}{'...' if len(task.description) > 100 else ''}\n"

            if "## Recent Ideas" in roadmap_content:
                # Insert after the Recent Ideas header
                parts = roadmap_content.split("## Recent Ideas\n")
                roadmap_content = (
                    parts[0] + "## Recent Ideas\n\n" + task_entry + "\n" + parts[1]
                    if len(parts) > 1
                    else parts[0] + "## Recent Ideas\n\n" + task_entry + "\n"
                )
            else:
                # Append to end
                roadmap_content += f"\n## Recent Ideas\n\n{task_entry}\n"

            # Write updated roadmap
            with open(self.roadmap_path, "w") as f:
                f.write(roadmap_content)

            console.log(f"Updated roadmap with task {task.id}")

        except Exception as e:
            console.log(f"Error updating roadmap: {e}")

    async def get_roadmap_summary(self) -> str:
        """Get a summary of the current roadmap."""
        try:
            if not self.roadmap_path.exists():
                return "No roadmap found."

            with open(self.roadmap_path) as f:
                content = f.read()

            # Extract key sections
            lines = content.split("\n")
            summary_lines = []

            for line in lines[:20]:  # First 20 lines
                if line.strip() and (line.startswith("#") or line.startswith("-")):
                    summary_lines.append(line.strip())

            return "\n".join(summary_lines) if summary_lines else "Empty roadmap."

        except Exception as e:
            return f"Error reading roadmap: {e}"


async def main():
    """Main entry point for communications agent."""
    import sys

    if len(sys.argv) < 2:
        console.log("Usage: python -m agents.communications.main <command>")
        return

    base_path = Path.cwd()
    agent = CommunicationsAgent(base_path)

    command = sys.argv[1]

    if command == "process_idea" and len(sys.argv) > 2:
        idea_text = " ".join(sys.argv[2:])
        task = await agent.process_idea(idea_text)
        console.log(f"Created task: {task.id}")

    elif command == "process_feedback" and len(sys.argv) > 2:
        feedback_text = " ".join(sys.argv[2:])
        task = await agent.process_feedback(feedback_text)
        if task:
            console.log(f"Created task: {task.id}")
        else:
            console.log("No task created from feedback")

    elif command == "roadmap_summary":
        summary = await agent.get_roadmap_summary()
        console.log(summary)

    else:
        console.log("Unknown command or missing arguments")


if __name__ == "__main__":
    asyncio.run(main())
