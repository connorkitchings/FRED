"""Tests for web_to_markdown utility."""

import unittest
from unittest.mock import Mock, patch

from src.fred_macro.utils.web_to_markdown import (
    FetchError,
    InvalidURLError,
    MarkdownResult,
    _validate_url,
    fetch_markdown,
)


class TestValidateUrl(unittest.TestCase):
    """Test URL validation."""

    def test_valid_http_url(self):
        """Test valid http URL passes."""
        _validate_url("http://example.com")  # Should not raise

    def test_valid_https_url(self):
        """Test valid https URL passes."""
        _validate_url("https://example.com/path")  # Should not raise

    def test_empty_url(self):
        """Test empty URL raises error."""
        with self.assertRaises(InvalidURLError):
            _validate_url("")

    def test_missing_scheme(self):
        """Test URL without scheme raises error."""
        with self.assertRaises(InvalidURLError):
            _validate_url("example.com")

    def test_invalid_scheme(self):
        """Test URL with invalid scheme raises error."""
        with self.assertRaises(InvalidURLError):
            _validate_url("ftp://example.com")

    def test_missing_netloc(self):
        """Test URL without netloc raises error."""
        with self.assertRaises(InvalidURLError):
            _validate_url("http://")


class TestMarkdownResult(unittest.TestCase):
    """Test MarkdownResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = MarkdownResult(
            content="# Title\n\nContent",
            url="https://example.com",
            method_used="text/markdown",
            tokens=100,
            content_type="text/markdown",
            retain_images=False,
            status_code=200,
        )

        data = result.to_dict()

        self.assertEqual(data["content"], "# Title\n\nContent")
        self.assertEqual(data["metadata"]["url"], "https://example.com")
        self.assertEqual(data["metadata"]["method_used"], "text/markdown")
        self.assertEqual(data["metadata"]["tokens"], 100)
        self.assertEqual(data["metadata"]["content_type"], "text/markdown")
        self.assertFalse(data["metadata"]["retain_images"])


class TestFetchMarkdown(unittest.TestCase):
    """Test fetch_markdown function."""

    @patch("src.fred_macro.utils.web_to_markdown._fetch_with_retry")
    def test_successful_fetch(self, mock_fetch):
        """Test successful markdown fetch."""
        mock_response = Mock()
        mock_response.text = "# Title\n\nContent"
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "text/markdown; charset=utf-8",
            "x-markdown-tokens": "150",
        }
        mock_fetch.return_value = mock_response

        result = fetch_markdown("https://example.com")

        self.assertEqual(result.content, "# Title\n\nContent")
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.tokens, 150)
        self.assertEqual(result.status_code, 200)

    @patch("src.fred_macro.utils.web_to_markdown._fetch_with_retry")
    def test_fetch_without_tokens_header(self, mock_fetch):
        """Test fetch when tokens header is missing."""
        mock_response = Mock()
        mock_response.text = "# Title"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/markdown"}
        mock_fetch.return_value = mock_response

        result = fetch_markdown("https://example.com")

        self.assertIsNone(result.tokens)
        self.assertEqual(result.content, "# Title")

    @patch("src.fred_macro.utils.web_to_markdown._fetch_with_retry")
    def test_fetch_with_method_override(self, mock_fetch):
        """Test fetch with method override."""
        mock_response = Mock()
        mock_response.text = "Content"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/markdown"}
        mock_fetch.return_value = mock_response

        result = fetch_markdown("https://example.com", method="browser")

        self.assertEqual(result.method_used, "browser")
        # Verify the URL includes the method parameter
        call_args = mock_fetch.call_args
        self.assertIn("method=browser", call_args[0][0])

    @patch("src.fred_macro.utils.web_to_markdown._fetch_with_retry")
    def test_fetch_with_retain_images(self, mock_fetch):
        """Test fetch with image retention."""
        mock_response = Mock()
        mock_response.text = "Content"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/markdown"}
        mock_fetch.return_value = mock_response

        result = fetch_markdown("https://example.com", retain_images=True)

        self.assertTrue(result.retain_images)
        # Verify the URL includes the retain_images parameter
        call_args = mock_fetch.call_args
        self.assertIn("retain_images=true", call_args[0][0])

    def test_invalid_url_raises_error(self):
        """Test that invalid URL raises InvalidURLError."""
        with self.assertRaises(InvalidURLError):
            fetch_markdown("not-a-valid-url")

    @patch("src.fred_macro.utils.web_to_markdown._fetch_with_retry")
    def test_fetch_error_raises_fetch_error(self, mock_fetch):
        """Test that fetch errors raise FetchError."""
        mock_fetch.side_effect = FetchError("Network error")

        with self.assertRaises(FetchError):
            fetch_markdown("https://example.com")


class TestFetchWithRetry(unittest.TestCase):
    """Test retry logic."""

    @patch("src.fred_macro.utils.web_to_markdown.requests.get")
    def test_successful_request_no_retry(self, mock_get):
        """Test successful request doesn't retry."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from src.fred_macro.utils.web_to_markdown import _fetch_with_retry

        result = _fetch_with_retry("https://markdown.new/test", 30)

        self.assertEqual(result, mock_response)
        mock_get.assert_called_once()

    @patch("src.fred_macro.utils.web_to_markdown.requests.get")
    def test_timeout_error_raises_fetch_error(self, mock_get):
        """Test timeout error raises FetchError."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        from src.fred_macro.utils.web_to_markdown import _fetch_with_retry

        with self.assertRaises(FetchError) as context:
            _fetch_with_retry("https://markdown.new/test", 30)

        self.assertIn("timed out", str(context.exception).lower())

    @patch("src.fred_macro.utils.web_to_markdown.requests.get")
    def test_connection_error_raises_fetch_error(self, mock_get):
        """Test connection error raises FetchError."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        from src.fred_macro.utils.web_to_markdown import _fetch_with_retry

        with self.assertRaises(FetchError) as context:
            _fetch_with_retry("https://markdown.new/test", 30)

        self.assertIn("connection", str(context.exception).lower())


class TestErrors(unittest.TestCase):
    """Test error classes."""

    def test_fetch_error_with_status_code(self):
        """Test FetchError stores status code."""
        error = FetchError("HTTP error", status_code=404)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(str(error), "HTTP error")

    def test_fetch_error_without_status_code(self):
        """Test FetchError without status code."""
        error = FetchError("Network error")
        self.assertIsNone(error.status_code)
        self.assertEqual(str(error), "Network error")

    def test_invalid_url_error_message(self):
        """Test InvalidURLError message."""
        error = InvalidURLError("Invalid URL format")
        self.assertEqual(str(error), "Invalid URL format")


if __name__ == "__main__":
    unittest.main()
