"""File system helpers for Obsidian vault integration."""

import shutil
from pathlib import Path

from rich.console import Console

from core.config import ConfigManager

console = Console()


class ObsidianVaultIntegration:
    """Integration with Obsidian vault for markdown file synchronization."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self._vault_path: Path | None = None

    @property
    def vault_path(self) -> Path | None:
        """Get the configured Obsidian vault path."""
        if self._vault_path is None:
            settings = self.config_manager.get_settings()
            if settings.obsidian_path:
                self._vault_path = Path(settings.obsidian_path)
                if not self._vault_path.exists():
                    console.log(
                        f"Warning: Obsidian vault path does not exist: {self._vault_path}"
                    )
                    return None
        return self._vault_path

    def is_enabled(self) -> bool:
        """Check if Obsidian integration is enabled and configured."""
        return self.vault_path is not None and self.vault_path.exists()

    async def sync_task_to_vault(self, task_file: Path) -> bool:
        """Sync a task markdown file to the Obsidian vault."""
        if not self.is_enabled():
            console.log("Obsidian vault integration not enabled or configured")
            return False

        try:
            # Create vault structure if it doesn't exist
            vault_tasks_dir = self.vault_path / "Nexus CLI" / "Tasks"
            vault_tasks_dir.mkdir(parents=True, exist_ok=True)

            # Determine target directory based on task status
            task_status = self._get_task_status_from_path(task_file)
            target_dir = vault_tasks_dir / task_status.title()
            target_dir.mkdir(exist_ok=True)

            # Copy task file to vault
            target_file = target_dir / task_file.name
            shutil.copy2(task_file, target_file)

            console.log(f"Synced task to vault: {target_file}")
            return True

        except Exception as e:
            console.log(f"Error syncing task to vault: {e}")
            return False

    async def sync_roadmap_to_vault(self) -> bool:
        """Sync the roadmap to the Obsidian vault."""
        if not self.is_enabled():
            return False

        try:
            roadmap_file = self.base_path / "docs" / "ROADMAP.md"
            if not roadmap_file.exists():
                console.log("No roadmap file to sync")
                return False

            # Create vault docs directory
            vault_docs_dir = self.vault_path / "Nexus CLI" / "Documentation"
            vault_docs_dir.mkdir(parents=True, exist_ok=True)

            # Copy roadmap to vault
            target_file = vault_docs_dir / "ROADMAP.md"
            shutil.copy2(roadmap_file, target_file)

            console.log(f"Synced roadmap to vault: {target_file}")
            return True

        except Exception as e:
            console.log(f"Error syncing roadmap to vault: {e}")
            return False

    async def sync_release_docs_to_vault(self, version: str) -> bool:
        """Sync release documentation to the Obsidian vault."""
        if not self.is_enabled():
            return False

        try:
            release_dir = self.base_path / "releases" / version
            if not release_dir.exists():
                console.log(f"No release directory found: {release_dir}")
                return False

            # Create vault releases directory
            vault_releases_dir = self.vault_path / "Nexus CLI" / "Releases" / version
            vault_releases_dir.mkdir(parents=True, exist_ok=True)

            # Sync all markdown files in release directory
            synced_files = []
            for md_file in release_dir.glob("*.md"):
                target_file = vault_releases_dir / md_file.name
                shutil.copy2(md_file, target_file)
                synced_files.append(target_file)

            if synced_files:
                console.log(f"Synced {len(synced_files)} release files to vault")
                return True
            else:
                console.log("No release files to sync")
                return False

        except Exception as e:
            console.log(f"Error syncing release docs to vault: {e}")
            return False

    async def sync_feedback_to_vault(self) -> bool:
        """Sync feedback files to the Obsidian vault."""
        if not self.is_enabled():
            return False

        try:
            feedback_dir = self.base_path / "vault" / "inbox" / "feedback"
            if not feedback_dir.exists():
                return True  # No feedback to sync

            # Create vault feedback directory
            vault_feedback_dir = self.vault_path / "Nexus CLI" / "Feedback"
            vault_feedback_dir.mkdir(parents=True, exist_ok=True)

            # Sync all feedback files
            synced_count = 0
            for feedback_file in feedback_dir.glob("*.md"):
                target_file = vault_feedback_dir / feedback_file.name
                if not target_file.exists():  # Only sync new files
                    shutil.copy2(feedback_file, target_file)
                    synced_count += 1

            if synced_count > 0:
                console.log(f"Synced {synced_count} feedback files to vault")

            return True

        except Exception as e:
            console.log(f"Error syncing feedback to vault: {e}")
            return False

    async def create_vault_index(self) -> bool:
        """Create an index file in the vault for easy navigation."""
        if not self.is_enabled():
            return False

        try:
            vault_nexus_dir = self.vault_path / "Nexus CLI"
            vault_nexus_dir.mkdir(exist_ok=True)

            # Create index content
            from datetime import datetime

            index_content = f"""# Nexus CLI - Development Hub

Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

This vault contains synchronized documentation and task tracking for the Nexus CLI project.

## Navigation

### 📋 Task Management
- [[Tasks/Inbox]] - New incoming tasks
- [[Tasks/Backlog]] - Scoped and prioritized tasks
- [[Tasks/Sprint]] - Currently active tasks
- [[Tasks/Done]] - Completed tasks

### 📚 Documentation
- [[Documentation/ROADMAP]] - Project roadmap and future plans
- [[Documentation/ARCHITECTURE]] - System architecture documentation

### 🚀 Releases
- [[Releases]] - Release documentation and notes

### 💬 Feedback
- [[Feedback]] - User feedback and suggestions

## Quick Links

### Recent Activity
Check the Tasks/Done folder for recently completed work.

### Current Sprint
See Tasks/Sprint for what's currently being worked on.

### Roadmap
Review Documentation/ROADMAP for upcoming features and long-term plans.

## Integration Notes

This vault is automatically synchronized with the Nexus CLI file system. Changes made here will be reflected in the main project, and vice versa.

### File Structure
```
Nexus CLI/
├── Tasks/
│   ├── Inbox/
│   ├── Backlog/
│   ├── Sprint/
│   └── Done/
├── Documentation/
├── Releases/
└── Feedback/
```

### Sync Status
- ✅ Tasks: Auto-synced on changes
- ✅ Documentation: Synced on updates
- ✅ Releases: Synced on creation
- ✅ Feedback: Synced on submission

---

*Generated by Nexus CLI Obsidian Integration*
"""

            # Write index file
            index_file = vault_nexus_dir / "README.md"
            with open(index_file, "w") as f:
                f.write(index_content)

            console.log(f"Created vault index: {index_file}")
            return True

        except Exception as e:
            console.log(f"Error creating vault index: {e}")
            return False

    def _get_task_status_from_path(self, task_file: Path) -> str:
        """Extract task status from file path."""
        # Look at the parent directory name to determine status
        parent = task_file.parent.name
        if parent in ["inbox", "backlog", "sprint", "done"]:
            return parent
        return "unknown"

    async def full_sync(self) -> bool:
        """Perform a full synchronization of all content to the vault."""
        if not self.is_enabled():
            console.log("Obsidian vault integration not available")
            return False

        console.log("Starting full vault synchronization...")

        success_count = 0
        total_operations = 0

        # Sync all task files
        task_dirs = ["inbox", "backlog", "sprint", "done"]
        for task_dir in task_dirs:
            task_path = self.base_path / "tasks" / task_dir
            if task_path.exists():
                for task_file in task_path.glob("*.md"):
                    total_operations += 1
                    if await self.sync_task_to_vault(task_file):
                        success_count += 1

        # Sync roadmap
        total_operations += 1
        if await self.sync_roadmap_to_vault():
            success_count += 1

        # Sync feedback
        total_operations += 1
        if await self.sync_feedback_to_vault():
            success_count += 1

        # Sync release docs
        releases_dir = self.base_path / "releases"
        if releases_dir.exists():
            for version_dir in releases_dir.iterdir():
                if version_dir.is_dir():
                    total_operations += 1
                    if await self.sync_release_docs_to_vault(version_dir.name):
                        success_count += 1

        # Create index
        total_operations += 1
        if await self.create_vault_index():
            success_count += 1

        console.log(
            f"Vault sync completed: {success_count}/{total_operations} operations successful"
        )
        return success_count == total_operations


async def main():
    """Main entry point for vault integration testing."""
    import sys

    base_path = Path.cwd()
    vault_integration = ObsidianVaultIntegration(base_path)

    if len(sys.argv) < 2:
        console.log("Usage: python -m connectors.vault.fs <command>")
        console.log("Commands: check, sync_all, sync_roadmap, create_index")
        return

    command = sys.argv[1]

    if command == "check":
        if vault_integration.is_enabled():
            console.log(
                f"✅ Obsidian vault integration enabled: {vault_integration.vault_path}"
            )
        else:
            console.log(
                "❌ Obsidian vault integration not configured or path doesn't exist"
            )
            console.log("Set OBSIDIAN_VAULT_PATH in your .env file")

    elif command == "sync_all":
        success = await vault_integration.full_sync()
        console.log(
            f"Full sync {'completed successfully' if success else 'completed with errors'}"
        )

    elif command == "sync_roadmap":
        success = await vault_integration.sync_roadmap_to_vault()
        console.log(f"Roadmap sync {'successful' if success else 'failed'}")

    elif command == "create_index":
        success = await vault_integration.create_vault_index()
        console.log(f"Index creation {'successful' if success else 'failed'}")

    else:
        console.log(f"Unknown command: {command}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
