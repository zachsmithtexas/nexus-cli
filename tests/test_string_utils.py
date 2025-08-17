"""Tests for string utilities."""

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
        assert not result.endswith("-")

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
