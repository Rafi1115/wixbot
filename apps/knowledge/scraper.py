import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

# tags that add zero useful content
JUNK_TAGS = [
    "script", "style", "nav", "footer", "header",
    "iframe", "noscript", "svg", "form", "button",
    "aside", "advertisement",
]

# common file extensions to skip
SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".mp4", ".mp3", ".zip", ".exe", ".dmg", ".css", ".js",
}


def is_valid_url(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to the same domain and is worth scraping."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.netloc != base_domain:
            return False
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
            return False
        return True
    except Exception:
        return False


def extract_text(soup: BeautifulSoup, url: str) -> str:
    """Extract clean readable text from a parsed HTML page."""
    # remove junk tags
    for tag in soup(JUNK_TAGS):
        tag.decompose()

    # try to get the main content area first
    main = (
        soup.find("main") or
        soup.find(id="content") or
        soup.find(class_="content") or
        soup.find("article") or
        soup.body
    )

    if not main:
        return ""

    text = main.get_text(separator=" ", strip=True)

    # clean up excessive whitespace
    import re
    text = re.sub(r"\s+", " ", text).strip()

    return text


def scrape_website(base_url: str, max_pages: int = 30) -> str:
    """
    Scrapes all pages on a website starting from base_url.
    Follows internal links. Returns all text combined.

    Args:
        base_url: The starting URL
        max_pages: Max pages to crawl (default 30, enough for most store sites)

    Returns:
        Combined text from all scraped pages
    """
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    visited = set()
    to_visit = [base_url]
    all_text = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)

        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Skipping {url} — status {response.status_code}")
                continue

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            # extract page title
            title = soup.title.string.strip() if soup.title else ""

            # extract clean text
            text = extract_text(soup, url)

            if text and len(text) > 100:
                page_content = f"[Page: {title or url}]\n{text}"
                all_text.append(page_content)
                logger.info(f"Scraped: {url} ({len(text)} chars)")

            # collect internal links to follow
            for link in soup.find_all("a", href=True):
                href = link["href"].strip()
                full_url = urljoin(url, href).split("#")[0]  # remove anchors
                if (
                    full_url not in visited
                    and full_url not in to_visit
                    and is_valid_url(full_url, base_domain)
                ):
                    to_visit.append(full_url)

        except requests.Timeout:
            logger.warning(f"Timeout scraping {url}")
        except requests.RequestException as e:
            logger.warning(f"Error scraping {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")

    combined = "\n\n".join(all_text)
    logger.info(f"Scrape complete: {len(visited)} pages, {len(combined)} total chars")
    return combined
