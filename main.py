#!/usr/bin/env python3
"""Main entry point for Nexus CLI."""

import asyncio
import sys
from pathlib import Path

from rich.console import Console

console = Console()


async def main():
    """Main entry point with command routing."""
    if len(sys.argv) < 2:
        console.log("Nexus CLI - Local-first 5-agent development stack")
        console.log("")
        console.log("Usage: python main.py <command> [args...]")
        console.log("")
        console.log("Commands:")
        console.log("  orchestrator  - Start the main orchestrator")
        console.log("  bot          - Start Discord bot")
        console.log("  demo         - Run demonstration workflow")
        console.log("  status       - Show system status")
        console.log("")
        console.log("Agent commands:")
        console.log("  comm <cmd>   - Communications agent")
        console.log("  pm <cmd>     - Project Manager agent")
        console.log("  senior <cmd> - Senior Developer agent")
        console.log("  junior <cmd> - Junior Developer agent")
        console.log("  qa <cmd>     - Release QA agent")
        console.log("")
        console.log("Use 'make help' for Makefile targets")
        return

    command = sys.argv[1]
    base_path = Path.cwd()

    try:
        if command == "orchestrator":
            from core.orchestrator import Orchestrator

            orchestrator = Orchestrator(base_path)
            await orchestrator.start()

        elif command == "bot":
            from connectors.discord.bot import start_bot

            await start_bot(base_path)

        elif command == "demo":
            await run_demo(base_path)

        elif command == "status":
            await show_status(base_path)

        elif command == "comm":
            await run_agent_command("communications", sys.argv[2:])

        elif command == "pm":
            await run_agent_command("project_manager", sys.argv[2:])

        elif command == "senior":
            await run_agent_command("senior_dev", sys.argv[2:])

        elif command == "junior":
            await run_agent_command("junior_dev", sys.argv[2:])

        elif command == "qa":
            await run_agent_command("release_qa", sys.argv[2:])

        else:
            console.log(f"Unknown command: {command}")
            sys.exit(1)

    except KeyboardInterrupt:
        console.log("Interrupted by user")
    except Exception as e:
        console.log(f"Error: {e}")
        sys.exit(1)


async def run_demo(base_path: Path):
    """Run the complete demonstration workflow."""
    console.log("🚀 Starting Nexus CLI Demonstration")
    console.log("=" * 50)

    # Import required modules
    from agents.communications.main import CommunicationsAgent
    from agents.junior_dev.main import JuniorDevAgent
    from agents.project_manager.main import ProjectManagerAgent
    from agents.release_qa.main import ReleaseQAAgent
    from agents.senior_dev.main import SeniorDevAgent
    from core.queue import TaskQueue

    # Initialize components
    comm_agent = CommunicationsAgent(base_path)
    pm_agent = ProjectManagerAgent(base_path)
    senior_agent = SeniorDevAgent(base_path)
    junior_agent = JuniorDevAgent(base_path)
    qa_agent = ReleaseQAAgent(base_path)
    task_queue = TaskQueue(base_path)

    console.log("✅ Agents initialized")

    # Step 1: Create a task from an idea
    console.log("\n📝 Step 1: Creating task from idea")
    idea = "Implement a slugify utility function that converts strings to URL-friendly slugs"
    task = await comm_agent.process_idea(idea)
    console.log(f"Created task: {task.id} - {task.title}")

    # Step 2: Project manager scopes the task
    console.log("\n📋 Step 2: Project Manager scoping task")
    success = await pm_agent.scope_task(task.id)
    if success:
        console.log("✅ Task scoped successfully")
        scoped_task = task_queue.get_task(task.id)
        console.log(f"Priority: {scoped_task.priority}")
        console.log(f"Assigned to: {scoped_task.assigned_agent}")

    # Step 3: Move to sprint
    console.log("\n🏃 Step 3: Moving to sprint")
    success = await pm_agent.move_to_sprint(task.id)
    if success:
        console.log("✅ Task moved to sprint")

    # Step 4: Junior dev implements the function
    console.log("\n👨‍💻 Step 4: Junior Developer implementation")
    success = await junior_agent.implement_function(task.id)
    if success:
        console.log("✅ Function implemented successfully")

    # Step 5: Create release documentation
    console.log("\n📦 Step 5: Creating release documentation")
    version = "v0.001"
    tests_success = await qa_agent.create_release_tests(version)
    notes_success = await qa_agent.create_release_notes(version)

    if tests_success and notes_success:
        console.log("✅ Release documentation created")

    # Step 6: Show final status
    console.log("\n📊 Step 6: Final system status")
    await show_status(base_path)

    console.log("\n🎉 Demo completed successfully!")
    console.log("\nGenerated files:")
    console.log("- utils/string_utils.py (slugify function)")
    console.log("- tests/test_string_utils.py (unit tests)")
    console.log("- releases/v0.001/TESTS.md")
    console.log("- releases/v0.001/NOTES.md")
    console.log("- docs/ROADMAP.md (updated)")


async def show_status(base_path: Path):
    """Show current system status."""
    from core.config import ConfigManager
    from core.queue import TaskQueue
    from core.router import ProviderRouter

    task_queue = TaskQueue(base_path)
    config_manager = ConfigManager(base_path / "config")
    router = ProviderRouter(config_manager)

    # Get queue counts
    queue_counts = task_queue.get_queue_counts()

    console.log("📊 Nexus CLI System Status")
    console.log("=" * 30)

    # Task queues
    console.log("\n📋 Task Queues:")
    for status, count in queue_counts.items():
        console.log(f"  {status.title()}: {count} tasks")

    total_tasks = sum(queue_counts.values())
    console.log(f"  Total: {total_tasks} tasks")

    # Available providers
    console.log("\n🔌 Available Providers:")
    providers = router.get_available_providers()
    if providers:
        for provider in providers:
            console.log(f"  ✅ {provider}")
    else:
        console.log("  ❌ No providers available")

    # Configuration status
    console.log("\n⚙️ Configuration:")
    settings = config_manager.get_settings()
    roles = config_manager.get_roles()
    models = config_manager.get_models()

    console.log(f"  Roles configured: {len(roles)}")
    console.log(f"  Models configured: {len(models)}")
    console.log(
        f"  Discord token: {'✅ Set' if settings.discord_token else '❌ Not set'}"
    )
    console.log(
        f"  Obsidian path: {'✅ Set' if settings.obsidian_path else '❌ Not set'}"
    )


async def run_agent_command(agent_name: str, args: list):
    """Run a command for a specific agent."""
    if not args:
        console.log(f"No command specified for {agent_name} agent")
        return

    # Import and run the agent's main function
    module_name = f"agents.{agent_name}.main"

    try:
        # Temporarily modify sys.argv for the agent
        old_argv = sys.argv
        sys.argv = [f"{module_name}.py"] + args

        if agent_name == "communications":
            from agents.communications.main import main as agent_main
        elif agent_name == "project_manager":
            from agents.project_manager.main import main as agent_main
        elif agent_name == "senior_dev":
            from agents.senior_dev.main import main as agent_main
        elif agent_name == "junior_dev":
            from agents.junior_dev.main import main as agent_main
        elif agent_name == "release_qa":
            from agents.release_qa.main import main as agent_main
        else:
            console.log(f"Unknown agent: {agent_name}")
            return

        await agent_main()

    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    asyncio.run(main())
