#!/usr/bin/env python3
"""Print current system status - queue counts and roadmap items."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

from core.queue import TaskQueue
from core.task import TaskStatus

console = Console()


def main():
    """Print system status."""
    base_path = Path(__file__).parent.parent
    task_queue = TaskQueue(base_path)

    # Get queue counts
    queue_counts = task_queue.get_queue_counts()

    console.print("📊 [bold blue]Nexus CLI Status[/bold blue]")
    console.print("=" * 30)

    # Task queues
    console.print("\n📋 [bold]Task Queues:[/bold]")
    total_tasks = 0
    for status, count in queue_counts.items():
        icon = {"inbox": "📥", "backlog": "📋", "sprint": "🏃", "done": "✅"}.get(
            status, "📄"
        )
        console.print(f"  {icon} {status.title()}: [bold]{count}[/bold] tasks")
        total_tasks += count

    console.print(f"  📊 Total: [bold cyan]{total_tasks}[/bold cyan] tasks")

    # Recent roadmap items
    roadmap_path = base_path / "docs" / "ROADMAP.md"
    if roadmap_path.exists():
        console.print("\n🗺️  [bold]Recent Roadmap Items:[/bold]")
        try:
            with open(roadmap_path) as f:
                lines = f.readlines()

            recent_ideas = []
            in_recent_section = False

            for line in lines:
                line = line.strip()
                if "## Recent Ideas" in line:
                    in_recent_section = True
                    continue
                elif line.startswith("## ") and in_recent_section:
                    break
                elif in_recent_section and line.startswith("- **"):
                    recent_ideas.append(line)

            if recent_ideas:
                for idea in recent_ideas[-5:]:  # Last 5 items
                    console.print(f"  {idea}")
            else:
                console.print("  No recent ideas")

        except Exception as e:
            console.print(f"  Error reading roadmap: {e}")
    else:
        console.print("\n🗺️  [bold]Roadmap:[/bold] Not found")

    # Recent activity
    done_tasks = task_queue.list_tasks(TaskStatus.DONE)
    if done_tasks:
        console.print("\n⚡ [bold]Recent Activity:[/bold]")
        for task in done_tasks[-3:]:  # Last 3 completed
            console.print(f"  ✅ {task.title} ([dim]{task.id}[/dim])")
    else:
        console.print("\n⚡ [bold]Recent Activity:[/bold] No completed tasks")

    console.print()


if __name__ == "__main__":
    main()
