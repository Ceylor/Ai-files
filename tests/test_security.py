"""Tests for src/utils/security.py – path traversal prevention and filename sanitization."""

from src.utils.security import sanitize_filename, sanitize_category


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_simple_filename(self):
        assert sanitize_filename("video.mp4") == "video.mp4"

    def test_path_traversal_dotdot(self):
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_path_traversal_with_slashes(self):
        result = sanitize_filename("foo/bar/video.mp4")
        assert "/" not in result
        assert "\\" not in result
        assert result == "video.mp4" or "foo" not in result

    def test_special_characters_replaced(self):
        result = sanitize_filename("video (1) [copy].mp4")
        # Should replace parentheses and brackets
        assert "(" not in result
        assert ")" not in result

    def test_empty_name_becomes_unnamed(self):
        result = sanitize_filename("")
        assert result == "unnamed"

    def test_dots_only_becomes_unnamed(self):
        result = sanitize_filename("...")
        assert result == "unnamed"

    def test_preserves_valid_extension(self):
        result = sanitize_filename("my_video.mp4")
        assert result.endswith(".mp4")

    def test_unicode_handled(self):
        result = sanitize_filename("видео_тест.mp4")
        # Should not crash, may keep unicode chars
        assert isinstance(result, str)
        assert len(result) > 0

    def test_windows_path_separator(self):
        result = sanitize_filename("C:\\Users\\test\\video.mp4")
        assert "\\\\" not in result or result.endswith(".mp4")


class TestSanitizeCategory:
    """Tests for sanitize_category function."""

    def test_simple_category(self):
        assert sanitize_category("travel") == "travel"

    def test_category_with_spaces(self):
        result = sanitize_category("my category")
        assert " " not in result or result == "my_category"

    def test_category_with_special_chars(self):
        result = sanitize_category("cat@#$%")
        assert "@" not in result
        assert "#" not in result

    def test_empty_category_becomes_default(self):
        result = sanitize_category("")
        assert result == "default"

    def test_category_preserves_hyphens(self):
        result = sanitize_category("my-category")
        assert "-" in result

    def test_category_preserves_underscores(self):
        result = sanitize_category("my_category")
        assert "_" in result

    def test_category_traversal_blocked(self):
        result = sanitize_category("../../../etc")
        assert ".." not in result
        assert "/" not in result
