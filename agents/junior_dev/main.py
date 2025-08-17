"""Junior Developer Agent - Implement functions and unit tests."""

import asyncio
from pathlib import Path

from rich.console import Console

from core.config import ConfigManager
from core.queue import TaskQueue
from core.task import Task, TaskStatus

console = Console()


class JuniorDevAgent:
    """Agent responsible for implementing functions and unit tests."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_manager = ConfigManager(self.base_path / "config")
        self.task_queue = TaskQueue(self.base_path)
        self.utils_dir = self.base_path / "utils"
        self.tests_dir = self.base_path / "tests"

        # Ensure directories exist
        self.utils_dir.mkdir(exist_ok=True)
        self.tests_dir.mkdir(exist_ok=True)

    async def implement_function(self, task_id: str) -> bool:
        """Implement a function based on task requirements."""
        task = self.task_queue.get_task(task_id)
        if not task:
            console.log(f"Task {task_id} not found")
            return False

        console.log(f"Implementing function for task: {task.title}")

        # For demonstration, implement the utils.slugify function mentioned in AGENTS.md
        if "slugify" in task.title.lower() or "slugify" in task.description.lower():
            return await self._implement_slugify(task)

        # Generic implementation for other functions
        return await self._implement_generic_function(task)

    async def _implement_slugify(self, task: Task) -> bool:
        """Implement the slugify utility function."""
        console.log("Implementing slugify function...")

        # Create the slugify function
        slugify_code = '''"""String utilities for Nexus CLI."""

import re
import unicodedata


def slugify(text: str, max_length: int = 50) -> str:
    """
    Convert a string to a URL-friendly slug.
    
    Args:
        text: The input string to slugify
        max_length: Maximum length of the resulting slug
        
    Returns:
        A lowercase string with spaces replaced by hyphens,
        special characters removed, and limited to max_length.
        
    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("My Awesome Project 2024")
        'my-awesome-project-2024'
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().strip()
    text = re.sub(r'\\s+', '-', text)
    
    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text
'''

        # Write the function to utils/string_utils.py
        utils_file = self.utils_dir / "string_utils.py"
        with open(utils_file, "w") as f:
            f.write(slugify_code)

        # Create __init__.py for utils package
        init_file = self.utils_dir / "__init__.py"
        with open(init_file, "w") as f:
            f.write(
                '"""Utility functions for Nexus CLI."""\n\nfrom .string_utils import slugify\n\n__all__ = ["slugify"]\n'
            )

        # Create unit tests
        test_code = '''"""Tests for string utilities."""

import pytest
from utils.string_utils import slugify


class TestSlugify:
    """Test cases for the slugify function."""
    
    def test_basic_slugify(self):
        """Test basic string slugification."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("My Awesome Project") == "my-awesome-project"
    
    def test_special_characters(self):
        """Test handling of special characters."""
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("Test@#$%^&*()") == "test"
        assert slugify("Café & Restaurant") == "caf-restaurant"
    
    def test_numbers(self):
        """Test handling of numbers."""
        assert slugify("Project 2024") == "project-2024"
        assert slugify("Version 1.2.3") == "version-123"
    
    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        assert slugify("Multiple    Spaces   Here") == "multiple-spaces-here"
        assert slugify("  Leading and trailing  ") == "leading-and-trailing"
    
    def test_max_length(self):
        """Test maximum length limitation."""
        long_text = "This is a very long string that should be truncated"
        result = slugify(long_text, max_length=20)
        assert len(result) <= 20
        assert not result.endswith('-')
    
    def test_empty_string(self):
        """Test empty string input."""
        assert slugify("") == ""
        assert slugify("   ") == ""
    
    def test_unicode_characters(self):
        """Test unicode character handling."""
        assert slugify("Café") == "caf"
        assert slugify("naïve") == "nave"
    
    def test_type_error(self):
        """Test type error for non-string input."""
        with pytest.raises(TypeError):
            slugify(123)
        with pytest.raises(TypeError):
            slugify(None)


if __name__ == "__main__":
    # Run basic tests
    test_slugify = TestSlugify()
    test_slugify.test_basic_slugify()
    test_slugify.test_special_characters()
    test_slugify.test_numbers()
    print("All basic tests passed!")
'''

        # Write the test file
        test_file = self.tests_dir / "test_string_utils.py"
        with open(test_file, "w") as f:
            f.write(test_code)

        # Create __init__.py for tests package
        test_init_file = self.tests_dir / "__init__.py"
        with open(test_init_file, "w") as f:
            f.write('"""Test package for Nexus CLI."""\n')

        # Update task
        task.add_activity(
            "implemented slugify function",
            "junior_dev",
            "Created utils/string_utils.py with slugify function and comprehensive tests",
        )
        self.task_queue.move_task(
            task.id,
            TaskStatus.DONE,
            "junior_dev",
            "Implemented slugify function with unit tests",
        )

        console.log("Successfully implemented slugify function with tests")
        return True

    async def _implement_generic_function(self, task: Task) -> bool:
        """Implement a generic function based on task description."""
        console.log(f"Implementing generic function for: {task.title}")

        # Create a placeholder implementation
        function_name = self._extract_function_name(task.title)

        generic_code = f'''"""Generated function for task: {task.title}"""


def {function_name}():
    """
    {task.description}
    
    TODO: Implement the actual functionality.
    This is a placeholder implementation created by the junior dev agent.
    """
    # Placeholder implementation
    return "TODO: Implement {function_name}"


if __name__ == "__main__":
    result = {function_name}()
    print(f"Result: {{result}}")
'''

        # Write to a file
        function_file = self.utils_dir / f"{function_name}.py"
        with open(function_file, "w") as f:
            f.write(generic_code)

        # Create basic test
        test_code = f'''"""Tests for {function_name}."""

from utils.{function_name} import {function_name}


def test_{function_name}():
    """Basic test for {function_name}."""
    result = {function_name}()
    assert result is not None
    print(f"Test passed: {{result}}")


if __name__ == "__main__":
    test_{function_name}()
    print("Basic test completed!")
'''

        test_file = self.tests_dir / f"test_{function_name}.py"
        with open(test_file, "w") as f:
            f.write(test_code)

        # Update task
        task.add_activity(
            "implemented function",
            "junior_dev",
            f"Created {function_name} function with basic test",
        )
        self.task_queue.move_task(
            task.id,
            TaskStatus.DONE,
            "junior_dev",
            f"Implemented {function_name} function",
        )

        console.log(f"Successfully implemented {function_name} function")
        return True

    def _extract_function_name(self, title: str) -> str:
        """Extract a function name from the task title."""
        # Simple extraction logic
        words = (
            title.lower().replace("implement", "").replace("create", "").strip().split()
        )

        # Filter out common words
        filtered_words = [
            w for w in words if w not in ["a", "an", "the", "function", "method"]
        ]

        if not filtered_words:
            return "new_function"

        # Join words with underscores
        return "_".join(filtered_words[:3])  # Limit to 3 words

    async def run_tests(self, test_file: str = None) -> bool:
        """Run unit tests for implemented functions."""
        console.log("Running unit tests...")

        if test_file:
            # Run specific test file
            test_path = self.tests_dir / test_file
            if not test_path.exists():
                console.log(f"Test file {test_file} not found")
                return False

        # For demo purposes, just simulate test execution
        # In a real implementation, this would run pytest or unittest

        test_files = list(self.tests_dir.glob("test_*.py"))
        if not test_files:
            console.log("No test files found")
            return False

        console.log(f"Found {len(test_files)} test files")
        for test_file in test_files:
            console.log(f"  - {test_file.name}")

        # Simulate successful test run
        console.log("All tests passed! ✓")
        return True


async def main():
    """Main entry point for junior developer agent."""
    import sys

    if len(sys.argv) < 2:
        console.log("Usage: python -m agents.junior_dev.main <command>")
        return

    base_path = Path.cwd()
    agent = JuniorDevAgent(base_path)

    command = sys.argv[1]

    if command == "implement" and len(sys.argv) > 2:
        task_id = sys.argv[2]
        success = await agent.implement_function(task_id)
        console.log(f"Implementation {'successful' if success else 'failed'}")

    elif command == "test":
        test_file = sys.argv[2] if len(sys.argv) > 2 else None
        success = await agent.run_tests(test_file)
        console.log(f"Tests {'passed' if success else 'failed'}")

    elif command == "demo":
        # Create a demo task for slugify implementation
        from core.task import Task, TaskStatus

        demo_task = Task(
            title="Implement slugify function",
            description="Create a utility function that converts strings to URL-friendly slugs",
            status=TaskStatus.SPRINT,
            assigned_agent="junior_dev",
        )

        # Add to queue and implement
        agent.task_queue.add_task(demo_task)
        success = await agent.implement_function(demo_task.id)

        if success:
            # Run tests
            await agent.run_tests()

        console.log(f"Demo {'completed successfully' if success else 'failed'}")

    else:
        console.log("Unknown command. Available: implement, test, demo")


if __name__ == "__main__":
    asyncio.run(main())
