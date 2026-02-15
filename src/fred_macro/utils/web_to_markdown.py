"""Web to Markdown conversion utility using markdown.new API.

This module provides a simple interface to convert web URLs into clean,
token-efficient markdown using the markdown.new service.

Example:
    >>> from fred_macro.utils.web_to_markdown import fetch_markdown
    >>> content, metadata = fetch_markdown("https://example.com/article")
    >>> print(f"Tokens: {metadata['tokens']}")

CLI Usage:
    $ python -m fred_macro.utils.web_to_markdown https://example.com
"""

import sys
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

MARKDOWN_NEW_BASE = "https://markdown.new"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


@dataclass
class MarkdownResult:
    """Result of a markdown conversion.

    Attributes:
        content: The markdown content
        url: Original URL that was fetched
        method_used: Conversion method used (text/markdown, ai, browser)
        tokens: Estimated token count (if available)
        content_type: Content-Type header from response
        retain_images: Whether images were retained
        status_code: HTTP status code
    """

    content: str
    url: str
    method_used: str = "auto"
    tokens: Optional[int] = None
    content_type: str = "text/markdown"
    retain_images: bool = False
    status_code: int = 200

    def to_dict(self) -> dict:
        """Convert result to dictionary format."""
        return {
            "content": self.content,
            "metadata": {
                "url": self.url,
                "method_used": self.method_used,
                "tokens": self.tokens,
                "content_type": self.content_type,
                "retain_images": self.retain_images,
            },
        }


class WebToMarkdownError(Exception):
    """Base exception for web-to-markdown errors."""

    pass


class InvalidURLError(WebToMarkdownError):
    """Raised when URL is invalid."""

    pass


class FetchError(WebToMarkdownError):
    """Raised when fetching fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _validate_url(url: str) -> None:
    """Validate that URL is properly formatted.

    Args:
        url: URL to validate

    Raises:
        InvalidURLError: If URL is invalid
    """
    if not url:
        raise InvalidURLError("URL cannot be empty")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise InvalidURLError(
            f"Invalid URL: {url}. Must include scheme (http:// or https://)"
        )

    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(f"URL scheme must be http or https, got: {parsed.scheme}")


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_with_retry(url: str, timeout: int) -> requests.Response:
    """Fetch URL with retry logic.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response object

    Raises:
        FetchError: If request fails
    """
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout as e:
        raise FetchError(f"Request timed out after {timeout}s: {e}")
    except requests.exceptions.ConnectionError as e:
        raise FetchError(f"Connection error: {e}")
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"HTTP error: {e}", status_code=e.response.status_code)
    except requests.exceptions.RequestException as e:
        raise FetchError(f"Request failed: {e}")


def fetch_markdown(
    url: str,
    method: Optional[str] = None,
    retain_images: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> MarkdownResult:
    """Fetch URL and convert to markdown using markdown.new.

    Uses markdown.new service which provides 80% token savings vs raw HTML
    through a three-tier pipeline: text/markdown negotiation → Workers AI →
    Browser Rendering.

    Args:
        url: URL to fetch and convert
        method: Conversion method override ('auto', 'ai', 'browser').
               Default 'auto' lets markdown.new choose best method.
        retain_images: Whether to retain images in output. Default False.
        timeout: Request timeout in seconds. Default 30.

    Returns:
        MarkdownResult containing content and metadata

    Raises:
        InvalidURLError: If URL is invalid
        FetchError: If fetching fails after retries

    Example:
        >>> result = fetch_markdown("https://docs.python.org/3/tutorial/")
        >>> print(f"Content length: {len(result.content)}")
        >>> print(f"Tokens: {result.tokens}")
    """
    _validate_url(url)

    # Build markdown.new URL
    encoded_url = quote(url, safe=":/?#[]@!$&'()*+,;=")
    markdown_url = f"{MARKDOWN_NEW_BASE}/{encoded_url}"

    # Add query parameters if specified
    params = []
    if method and method != "auto":
        params.append(f"method={method}")
    if retain_images:
        params.append("retain_images=true")

    if params:
        markdown_url += "?" + "&".join(params)

    # Fetch with retry logic
    response = _fetch_with_retry(markdown_url, timeout)

    # Extract metadata from headers
    tokens = None
    tokens_header = response.headers.get("x-markdown-tokens")
    if tokens_header:
        try:
            tokens = int(tokens_header)
        except (ValueError, TypeError):
            pass  # Keep None if parsing fails

    content_type = response.headers.get("content-type", "text/markdown")

    # Determine method used from response or fallback to parameter
    if method and method != "auto":
        method_used = method
    elif "markdown" in content_type.lower():
        method_used = "text/markdown"
    else:
        method_used = "auto"

    # Read content
    content = response.text

    return MarkdownResult(
        content=content,
        url=url,
        method_used=method_used,
        tokens=tokens,
        content_type=content_type,
        retain_images=retain_images,
        status_code=response.status_code,
    )


def main() -> None:
    """CLI entry point for web-to-markdown conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert web URLs to markdown using markdown.new",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m fred_macro.utils.web_to_markdown https://example.com
  python -m fred_macro.utils.web_to_markdown https://example.com --method browser
  python -m fred_macro.utils.web_to_markdown https://example.com --retain-images
        """,
    )

    parser.add_argument("url", help="URL to convert to markdown")
    parser.add_argument(
        "--method",
        choices=["auto", "ai", "browser"],
        default="auto",
        help="Conversion method (default: auto)",
    )
    parser.add_argument(
        "--retain-images",
        action="store_true",
        help="Retain images in output",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only print metadata, not content",
    )

    args = parser.parse_args()

    try:
        result = fetch_markdown(
            url=args.url,
            method=args.method if args.method != "auto" else None,
            retain_images=args.retain_images,
            timeout=args.timeout,
        )

        if args.metadata_only:
            print(f"URL: {result.url}")
            print(f"Method: {result.method_used}")
            print(f"Tokens: {result.tokens or 'unknown'}")
            print(f"Content-Type: {result.content_type}")
            print(f"Content Length: {len(result.content)} chars")
        else:
            print(result.content)

        sys.exit(0)

    except InvalidURLError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FetchError as e:
        print(f"Error: {e}", file=sys.stderr)
        if e.status_code:
            print(f"HTTP Status: {e.status_code}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
