"""Task models and state management."""

import uuid
from datetime import datetime
from enum import Enum

import yaml
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    INBOX = "inbox"
    BACKLOG = "backlog"
    SPRINT = "sprint"
    DONE = "done"


class ActivityEntry(BaseModel):
    """Activity log entry for task transitions."""

    timestamp: datetime
    action: str
    agent: str
    details: str | None = None


class Task(BaseModel):
    """Task model with front matter and markdown content."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str
    status: TaskStatus = TaskStatus.INBOX
    priority: str = "medium"
    tags: list[str] = Field(default_factory=list)
    assigned_agent: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    activity: list[ActivityEntry] = Field(default_factory=list)

    def add_activity(self, action: str, agent: str, details: str | None = None):
        """Add an activity entry."""
        self.activity.append(
            ActivityEntry(
                timestamp=datetime.now(), action=action, agent=agent, details=details
            )
        )
        self.updated_at = datetime.now()

    def to_markdown(self) -> str:
        """Convert task to markdown format with front matter."""
        front_matter = {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "priority": self.priority,
            "tags": self.tags,
            "assigned_agent": self.assigned_agent,
            "acceptance_criteria": self.acceptance_criteria,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---\n\n"
        content += f"# {self.title}\n\n"
        content += f"{self.description}\n\n"

        if self.acceptance_criteria:
            content += "## Acceptance Criteria\n\n"
            for criterion in self.acceptance_criteria:
                content += f"- {criterion}\n"
            content += "\n"

        if self.activity:
            content += "## Activity\n\n"
            for entry in self.activity:
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                content += f"- **{timestamp}** [{entry.agent}] {entry.action}"
                if entry.details:
                    content += f": {entry.details}"
                content += "\n"

        return content

    @classmethod
    def from_markdown(cls, content: str) -> "Task":
        """Parse task from markdown content with front matter."""
        if not content.startswith("---"):
            # Simple markdown without front matter
            lines = content.strip().split("\n")
            title = lines[0].lstrip("# ").strip() if lines else "Untitled"
            description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            return cls(title=title, description=description)

        # Parse front matter
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid markdown format")

        front_matter = yaml.safe_load(parts[1])
        markdown_content = parts[2].strip()

        # Extract description from markdown content
        lines = markdown_content.split("\n")
        description_lines = []
        in_description = False

        for line in lines:
            if line.startswith("# "):
                in_description = True
                continue
            elif line.startswith("## "):
                break
            elif in_description:
                description_lines.append(line)

        description = "\n".join(description_lines).strip()

        # Parse activity entries
        activity = []
        for entry_data in front_matter.get("activity", []):
            if isinstance(entry_data, dict):
                activity.append(ActivityEntry(**entry_data))

        return cls(
            id=front_matter.get("id", str(uuid.uuid4())[:8]),
            title=front_matter.get("title", "Untitled"),
            description=description,
            status=TaskStatus(front_matter.get("status", "inbox")),
            priority=front_matter.get("priority", "medium"),
            tags=front_matter.get("tags", []),
            assigned_agent=front_matter.get("assigned_agent"),
            acceptance_criteria=front_matter.get("acceptance_criteria", []),
            created_at=datetime.fromisoformat(
                front_matter.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                front_matter.get("updated_at", datetime.now().isoformat())
            ),
            activity=activity,
        )
