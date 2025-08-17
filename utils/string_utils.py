"""String utilities for Nexus CLI."""

import re
import unicodedata


def slugify(text: str, max_length: int = 50) -> str:
    """Convert a string to a URL-friendly slug.

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
    text = unicodedata.normalize("NFKD", text)

    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().strip()
    text = re.sub(r"\s+", "-", text)

    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Remove consecutive hyphens
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")

    return text
