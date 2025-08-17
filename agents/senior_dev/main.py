"""Senior Developer Agent - Handle complex tasks and create subtasks for juniors."""

import asyncio
from pathlib import Path

from rich.console import Console

from core.config import ConfigManager
from core.queue import TaskQueue
from core.task import Task, TaskStatus

console = Console()


class SeniorDevAgent:
    """Agent responsible for complex development tasks and mentoring junior developers."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)

    async def analyze_task(self, task_id: str) -> dict:
        """Analyze a task to determine complexity and approach."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return {}

        console.log(f"Analyzing task: {task.title}")

        # Simple complexity analysis
        complexity_indicators = {
            "simple": ["fix typo", "update docs", "add comment", "simple function"],
            "moderate": ["implement function", "add feature", "refactor", "optimize"],
            "complex": ["design", "architecture", "integration", "framework", "system"],
        }

        description_lower = task.description.lower()
        title_lower = task.title.lower()
        combined_text = f"{title_lower} {description_lower}"

        complexity = "moderate"  # default
        for level, indicators in complexity_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                complexity = level
                break

        # Determine if task should be broken down
        should_break_down = (
            complexity == "complex"
            or len(task.description.split()) > 50
            or "and" in title_lower
            or "," in title_lower
        )

        analysis = {
            "complexity": complexity,
            "should_break_down": should_break_down,
            "estimated_effort": self._estimate_effort(complexity),
            "recommended_approach": self._get_approach(complexity),
        }

        task.add_activity(
            "analyzed by senior dev",
            "senior_dev",
            f"Complexity: {complexity}, Break down: {should_break_down}",
        )
        self.task_queue.update_task(task)

        console.log(f"Task analysis complete - Complexity: {complexity}")
        return analysis

    def _estimate_effort(self, complexity: str) -> str:
        """Estimate effort based on complexity."""
        effort_map = {
            "simple": "1-2 hours",
            "moderate": "4-8 hours",
            "complex": "1-3 days",
        }
        return effort_map.get(complexity, "Unknown")

    def _get_approach(self, complexity: str) -> str:
        """Get recommended approach based on complexity."""
        approach_map = {
            "simple": "Direct implementation, minimal planning needed",
            "moderate": "Design first, implement with testing, review",
            "complex": "Detailed design, break into subtasks, architecture review",
        }
        return approach_map.get(complexity, "Standard development process")

    async def break_down_task(self, task_id: str) -> list[str]:
        """Break down a complex task into smaller subtasks."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return []

        console.log(f"Breaking down task: {task.title}")

        # Simple task breakdown logic - in real implementation would use AI
        subtasks = []

        if "implement" in task.title.lower():
            # Implementation task breakdown
            base_name = task.title.replace("Implement", "").strip()

            subtasks_data = [
                {
                    "title": f"Design {base_name}",
                    "desc": f"Create design and architecture for {base_name}",
                },
                {
                    "title": f"Implement core {base_name}",
                    "desc": f"Implement the main functionality for {base_name}",
                },
                {
                    "title": f"Add tests for {base_name}",
                    "desc": f"Write unit tests for {base_name}",
                },
                {
                    "title": f"Document {base_name}",
                    "desc": f"Add documentation for {base_name}",
                },
            ]

        elif "feature" in task.title.lower():
            # Feature development breakdown
            base_name = task.title.replace("feature", "").replace("Feature", "").strip()

            subtasks_data = [
                {
                    "title": f"Spec out {base_name}",
                    "desc": f"Define requirements and specifications for {base_name}",
                },
                {
                    "title": f"Implement {base_name} backend",
                    "desc": f"Implement backend logic for {base_name}",
                },
                {
                    "title": f"Implement {base_name} frontend",
                    "desc": f"Implement user interface for {base_name}",
                },
                {
                    "title": f"Test {base_name} integration",
                    "desc": f"Test end-to-end functionality of {base_name}",
                },
            ]

        else:
            # Generic breakdown
            subtasks_data = [
                {
                    "title": f"Plan: {task.title}",
                    "desc": f"Plan and design approach for: {task.description[:100]}",
                },
                {
                    "title": f"Implement: {task.title}",
                    "desc": f"Core implementation of: {task.description[:100]}",
                },
                {
                    "title": f"Test: {task.title}",
                    "desc": f"Testing and validation of: {task.description[:100]}",
                },
            ]

        # Create subtasks
        created_subtasks = []
        for i, subtask_data in enumerate(subtasks_data):
            subtask = Task(
                title=subtask_data["title"],
                description=subtask_data["desc"],
                status=TaskStatus.BACKLOG,
                priority=task.priority,
                tags=task.tags + ["subtask", f"parent:{task.id}"],
                assigned_agent="junior_dev"
                if i > 0
                else "senior_dev",  # Senior does planning, junior does implementation
            )

            subtask.add_activity(
                "created as subtask", "senior_dev", f"Subtask of {task.id}"
            )

            self.task_queue.add_task(subtask)
            created_subtasks.append(subtask.id)

        # Update parent task
        task.add_activity(
            "broken down into subtasks",
            "senior_dev",
            f"Created {len(created_subtasks)} subtasks: {', '.join(created_subtasks)}",
        )
        task.tags.append("parent-task")

        # Move parent to done (work is now in subtasks)
        self.task_queue.move_task(
            task_id, TaskStatus.DONE, "senior_dev", "Task broken down into subtasks"
        )

        console.log(f"Created {len(created_subtasks)} subtasks for {task_id}")
        return created_subtasks

    async def handle_complex_task(self, task_id: str) -> bool:
        """Handle a complex task - either implement directly or break down."""
        analysis = await self.analyze_task(task_id)

        if not analysis:
            return False

        if analysis["should_break_down"]:
            console.log(f"Task {task_id} is complex, breaking down...")
            subtasks = await self.break_down_task(task_id)
            return len(subtasks) > 0
        else:
            console.log(f"Task {task_id} can be handled directly")
            # For demo purposes, just mark as done
            task = self.task_queue.get_task(task_id)
            if task:
                task.add_activity(
                    "completed by senior dev",
                    "senior_dev",
                    "Task completed directly without breakdown",
                )
                self.task_queue.move_task(
                    task_id, TaskStatus.DONE, "senior_dev", "Completed complex task"
                )
                return True

        return False

    async def review_junior_work(self, task_id: str) -> bool:
        """Review work completed by junior developer."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return False

        console.log(f"Reviewing junior work on: {task.title}")

        # Simplified review - in real implementation would check actual code
        # For demo, assume review passes
        task.add_activity(
            "reviewed by senior dev", "senior_dev", "Code review completed - approved"
        )
        self.task_queue.update_task(task)

        console.log(f"Review completed for task {task_id}")
        return True


async def main():
    """Main entry point for senior developer agent."""
    import sys

    if len(sys.argv) < 2:
        console.log("Usage: python -m agents.senior_dev.main <command>")
        return

    base_path = Path.cwd()
    agent = SeniorDevAgent(base_path)

    command = sys.argv[1]

    if command == "analyze_task" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        analysis = await agent.analyze_task(task_id)
        console.log(f"Analysis: {analysis}")

    elif command == "break_down_task" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        subtasks = await agent.break_down_task(task_id)
        console.log(f"Created subtasks: {subtasks}")

    elif command == "handle_task" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        success = await agent.handle_complex_task(task_id)
        console.log(f"Task handling {'successful' if success else 'failed'}")

    elif command == "review_work" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        success = await agent.review_junior_work(task_id)
        console.log(f"Review {'completed' if success else 'failed'}")

    else:
        console.log("Unknown command or missing arguments")


if __name__ == "__main__":
    asyncio.run(main())
