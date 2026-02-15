---
name: web-research
description: "Research web sources efficiently using markdown.new to convert URLs to clean, token-efficient markdown. Reduces token usage by 80% vs raw HTML."
metadata:
  trigger-keywords: "research, web, url, fetch, markdown, scrape, crawl, markdown.new"
  trigger-patterns: "^research web, ^fetch url, ^web research, ^markdown.new"
---

# Web Research Skill

Use markdown.new to convert any web URL into clean, AI-ready markdown. This saves ~80% on tokens compared to raw HTML.

## When to Use

- Researching external documentation or sources
- Gathering information from web pages
- Archiving web content for analysis
- Building knowledge bases from web sources
- Any task requiring web content in markdown format

## Quick Usage

### Method 1: Direct URL (Browser)
Prepend `markdown.new/` to any URL:

```
https://markdown.new/https://example.com/article
```

### Method 2: API (Programmatic)

```python
from fred_macro.utils.web_to_markdown import fetch_markdown

markdown_content, metadata = fetch_markdown("https://example.com/article")
print(f"Token count: {metadata.get('tokens', 'unknown')}")
```

### Method 3: CLI

```bash
python -m fred_macro.utils.web_to_markdown https://example.com/article
```

## How It Works (Three-Tier Pipeline)

markdown.new tries the fastest method first, falling back automatically:

1. **Primary**: Cloudflare `text/markdown` content negotiation
   - Returns clean markdown directly from edge-enabled sites
   - Zero parsing needed

2. **Fallback 1**: Workers AI `toMarkdown()`
   - If HTML is returned, converts it via AI
   - Fast conversion without re-fetch

3. **Fallback 2**: Browser Rendering API
   - For JavaScript-heavy pages
   - Full headless browser rendering

## Token Savings

| Format | Tokens (example blog post) |
|--------|---------------------------|
| Raw HTML | ~16,180 |
| markdown.new | ~3,150 |
| **Savings** | **~80%** |

## Configuration Options

### Method Override
Force a specific conversion method:

```python
fetch_markdown(url, method="browser")  # JS-heavy sites
fetch_markdown(url, method="ai")       # Workers AI
```

### Image Retention
By default, images are removed. To keep them:

```python
fetch_markdown(url, retain_images=True)
```

Or via URL:
```
https://markdown.new/https://example.com?method=browser&retain_images=true
```

## Error Handling

The utility handles common errors gracefully:

- **Network errors**: Retries with exponential backoff
- **Invalid URLs**: Raises `ValueError` with clear message
- **Non-200 responses**: Returns structured error with status code
- **Timeout**: Configurable timeout (default 30s)

## Response Format

```python
{
    "content": "# Clean Markdown\n\nArticle content...",
    "metadata": {
        "url": "https://example.com/article",
        "method_used": "text/markdown",  # or "ai", "browser"
        "tokens": 3150,
        "content_type": "text/markdown; charset=utf-8",
        "retain_images": False
    }
}
```

## Rate Limits and Best Practices

- **Be respectful**: Check robots.txt before bulk fetching
- **Cache results**: Store fetched markdown to avoid re-fetching
- **Rate limit**: Add delays between requests (1-2s minimum)
- **Respect ToS**: Verify external site terms of service
- **Error gracefully**: Always handle network failures

## Common Use Cases

### Research Agent Workflow

```python
from fred_macro.utils.web_to_markdown import fetch_markdown

urls_to_research = [
    "https://docs.python.org/3/library/asyncio.html",
    "https://fastapi.tiangolo.com/tutorial/",
]

for url in urls_to_research:
    try:
        content, meta = fetch_markdown(url)
        # Save to knowledge base or analyze
        print(f"Fetched {meta['tokens']} tokens from {url}")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
```

### DataOps - Documentation Ingestion

```python
# Fetch API documentation for local indexing
docs = fetch_markdown(
    "https://api.example.com/docs",
    retain_images=True  # Keep diagrams
)
```

### Quick Manual Research

Just prepend `markdown.new/` to any URL in your browser:
```
https://markdown.new/https://en.wikipedia.org/wiki/Python_(programming_language)
```

## Validation

Before using, verify:
- [ ] URL is valid and accessible
- [ ] robots.txt permits crawling (for bulk operations)
- [ ] Content license allows storage/analysis
- [ ] Network connectivity available

## Common Mistakes to Avoid

1. **Not checking robots.txt** - Respect site crawling policies
2. **No error handling** - Network requests can fail
3. **Fetching without caching** - Re-fetching wastes tokens and bandwidth
4. **Ignoring rate limits** - Can get IP blocked
5. **Forgetting image retention** - Diagrams/code snippets may be lost

## Links

- markdown.new: https://markdown.new/
- API docs: https://markdown.new/
- Source code: `src/fred_macro/utils/web_to_markdown.py`
- Tests: `tests/utils/test_web_to_markdown.py`
- Researcher agent: `AGENTS.md` → Researcher section

---

**Use markdown.new for all web research. Save tokens, get clean markdown.**
