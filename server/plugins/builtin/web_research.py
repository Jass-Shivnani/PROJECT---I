"""
Dione AI — Web Research & Scraping Plugin (Sovereign Edition)

Provides hardened real-time web intelligence:
- Multi-source resilient web search (DuckDuckGo HTML GET + Wikipedia API + Instant Answers)
- Sovereign SSRF-protected web scraping with clean HTML text extraction
- Robust HTTPS arXiv academic paper research with XML ElementTree parsing
- Windows CP1252 ASCII-safe stream encoding protection
"""

import re
import html
import socket
import ipaddress
import urllib.parse
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from loguru import logger
import httpx

from server.plugins.base import BasePlugin, dione_tool


def _to_ascii_safe(text: str) -> str:
    """Ensure text is safe for Windows terminal and stream encoding (CP1252)."""
    if not text:
        return ""
    return text.encode("ascii", errors="replace").decode("ascii")


class HTMLTextExtractor(HTMLParser):
    """Clean HTML text extractor that removes scripts, styles, and extracts readable text."""

    def __init__(self):
        super().__init__()
        self.result: List[str] = []
        self.skip_tags = {
            "script", "style", "nav", "header", "footer", "noscript",
            "svg", "form", "button", "aside"
        }
        self._current_tag = None
        self._skip = False
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag.lower()
        if self._current_tag in self.skip_tags:
            self._skip = True
        elif self._current_tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            self._skip = False
        elif tag.lower() == "title":
            self._in_title = False
        self._current_tag = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._skip:
            clean = data.strip()
            if clean:
                self.result.append(clean)

    def get_text(self) -> str:
        return " ".join(self.result)


class WebResearchPlugin(BasePlugin):
    """Web search, content scraping, and academic research synthesis."""

    name = "WebResearchPlugin"
    description = "Search the live web, scrape web pages with SSRF protection, and research academic papers"
    version = "0.3.0"

    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (DioneSovereignAssistant/1.0; contact: admin@dione-agent.local)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    WIKI_HEADERS = {
        "User-Agent": "DioneSovereignAssistant/1.0 (Mozilla/5.0 Windows NT 10.0; contact: admin@dione-agent.local)",
        "Accept": "application/json",
    }

    def _validate_ssrf_safety(self, url: str) -> Optional[str]:
        """Verify that the target URL does not resolve to private, loopback, or metadata addresses."""
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return "Invalid URL: Missing hostname."

            # Direct hostname check
            if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
                return f"SSRF Guard: Scraping local host '{hostname}' is prohibited."

            # Resolve DNS and verify IP
            ip_str = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip_str)

            if ip_obj.is_loopback:
                return f"SSRF Guard: Target '{hostname}' resolves to loopback IP {ip_str}."
            if ip_obj.is_private:
                return f"SSRF Guard: Target '{hostname}' resolves to private subnet IP {ip_str}."
            if ip_obj.is_link_local:
                return f"SSRF Guard: Target '{hostname}' resolves to link-local/cloud metadata IP {ip_str}."

            return None
        except socket.gaierror:
            return f"DNS resolution failed for hostname '{parsed.hostname}'."
        except Exception as e:
            return f"SSRF security check failed: {e}"

    @dione_tool(
        description="Search the web for current technical topics, facts, and public documentation",
        permission_level="read",
    )
    async def web_search(self, query: str, max_results: int = 5) -> str:
        """Search the web via resilient multi-source API integration (DuckDuckGo + Wikipedia).
        
        :param query: The search query string
        :param max_results: Maximum number of results to return (default: 5)
        """
        logger.info(f"[WebResearchPlugin] Web search query: {query}")
        results: List[str] = []

        # 1. DuckDuckGo HTML GET Search
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=self.BROWSER_HEADERS, follow_redirects=True) as client:
                ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
                resp = await client.get(ddg_url)
                if resp.status_code == 200 and "result__snippet" in resp.text:
                    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    urls = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', resp.text, re.DOTALL)

                    for i in range(min(len(snippets), max_results)):
                        clean_snippet = re.sub(r"<[^>]+>", "", html.unescape(snippets[i])).strip()
                        clean_url = re.sub(r"<[^>]+>", "", html.unescape(urls[i] if i < len(urls) else "")).strip()
                        if clean_snippet:
                            results.append(f"[{i+1}] {clean_snippet}\n    Source: {clean_url or 'DuckDuckGo'}")
        except Exception as e:
            logger.debug(f"[WebResearchPlugin] DuckDuckGo HTML notice: {e}")

        # 2. Wikipedia Full-Text Search API (Enrichment / Fallback)
        if len(results) < max_results:
            try:
                async with httpx.AsyncClient(timeout=8.0, headers=self.WIKI_HEADERS) as client:
                    wiki_api = (
                        f"https://en.wikipedia.org/w/api.php?action=query&list=search"
                        f"&srsearch={urllib.parse.quote_plus(query)}&utf8=&format=json&srlimit={max_results}"
                    )
                    wiki_resp = await client.get(wiki_api)
                    if wiki_resp.status_code == 200:
                        wiki_data = wiki_resp.json()
                        search_items = wiki_data.get("query", {}).get("search", [])

                        for item in search_items:
                            if len(results) >= max_results:
                                break
                            title = item.get("title", "")
                            raw_snippet = item.get("snippet", "")
                            clean_snippet = re.sub(r"<[^>]+>", "", html.unescape(raw_snippet)).strip()
                            article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                            results.append(f"* [Wikipedia] {title}: {clean_snippet}...\n  Link: {article_url}")
            except Exception as e:
                logger.debug(f"[WebResearchPlugin] Wikipedia search fallback notice: {e}")

        # 3. DuckDuckGo Instant Answer API (if still needed)
        if not results:
            try:
                async with httpx.AsyncClient(timeout=8.0, headers=self.BROWSER_HEADERS) as client:
                    ddg_api = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
                    resp = await client.get(ddg_api)
                    if resp.status_code == 200:
                        data = resp.json()
                        heading = data.get("Heading", "")
                        abstract = data.get("Abstract", "")
                        source_url = data.get("AbstractURL", "")

                        if abstract:
                            results.append(f"[Primary Abstract] {heading}: {abstract}\nSource: {source_url}")
            except Exception as e:
                logger.debug(f"[WebResearchPlugin] DuckDuckGo API notice: {e}")

        if results:
            header = f"=== Live Web Search Results for '{query}' ==="
            full_text = header + "\n\n" + "\n\n".join(results[:max_results])
            return _to_ascii_safe(full_text)

        return f"No direct search results found for '{query}'. Please try refining the keywords."

    @dione_tool(
        description="Scrape and extract clean readable text content from any public webpage or URL with SSRF protection",
        permission_level="read",
    )
    async def scrape_url(self, url: str, max_chars: int = 3000) -> str:
        """Fetch and extract readable text from a URL safely.
        
        :param url: The public webpage URL to scrape
        :param max_chars: Maximum characters of text to return (default: 3000)
        """
        logger.info(f"[WebResearchPlugin] Scraping URL: {url}")

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        # SSRF Security Validation
        ssrf_error = self._validate_ssrf_safety(url)
        if ssrf_error:
            logger.warning(f"[WebResearchPlugin] SSRF blocked target '{url}': {ssrf_error}")
            return f"SECURITY REFUSAL: {ssrf_error}"

        try:
            async with httpx.AsyncClient(timeout=12.0, headers=self.BROWSER_HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return f"HTTP error {resp.status_code} while fetching {url}."

                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    return _to_ascii_safe(resp.text[:max_chars])

                parser = HTMLTextExtractor()
                parser.feed(resp.text)
                extracted_text = parser.get_text()

                # Clean multiple whitespaces
                extracted_text = re.sub(r"\s+", " ", extracted_text).strip()
                title_prefix = f"Page Title: {parser.title}\nURL: {url}\n\n" if parser.title else f"URL: {url}\n\n"

                if not extracted_text:
                    return f"Successfully reached {url}, but no readable textual content could be parsed."

                full_output = title_prefix + extracted_text[:max_chars]
                return _to_ascii_safe(full_output)
        except httpx.TimeoutException:
            return f"Timeout error: The server at {url} took longer than 12 seconds to respond."
        except Exception as e:
            logger.error(f"[WebResearchPlugin] Scrape error for '{url}': {e}")
            return f"Failed to scrape {url}: {e}"

    @dione_tool(
        description="Search arXiv academic research papers by topic with full authors, citations, and abstracts",
        permission_level="read",
    )
    async def search_academic_papers(self, topic: str, max_results: int = 3) -> str:
        """Search arXiv.org for academic research papers and parse full Atom XML metadata.
        
        :param topic: Research topic or title keywords (e.g. 'Large Action Models')
        :param max_results: Number of papers to fetch (default: 3)
        """
        logger.info(f"[WebResearchPlugin] Searching arXiv academic papers for: {topic}")
        clean_topic = re.sub(r"[^\w\s]", "", topic).replace(" ", "+")
        api_url = f"https://export.arxiv.org/api/query?search_query=all:{clean_topic}&start=0&max_results={max(1, min(max_results, 10))}"

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=self.BROWSER_HEADERS, follow_redirects=True) as client:
                resp = await client.get(api_url)
                if resp.status_code != 200:
                    return f"arXiv API error (HTTP {resp.status_code})."

                root = ET.fromstring(resp.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)

                if not entries:
                    return f"No academic papers found on arXiv for topic '{topic}'."

                summaries: List[str] = []
                for i, entry in enumerate(entries[:max_results]):
                    title_elem = entry.find("atom:title", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    id_elem = entry.find("atom:id", ns)
                    published_elem = entry.find("atom:published", ns)

                    title = re.sub(r"\s+", " ", title_elem.text).strip() if title_elem is not None and title_elem.text else "Unknown Title"
                    summary = re.sub(r"\s+", " ", summary_elem.text).strip() if summary_elem is not None and summary_elem.text else "No abstract available."
                    paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                    pdf_url = paper_url.replace("/abs/", "/pdf/") if "/abs/" in paper_url else paper_url

                    # Extract authors
                    author_elems = entry.findall("atom:author/atom:name", ns)
                    authors = [a.text.strip() for a in author_elems if a.text][:4]
                    author_str = ", ".join(authors) + (" et al." if len(author_elems) > 4 else "")

                    pub_date = published_elem.text[:10] if published_elem is not None and published_elem.text else "Recent"

                    paper_block = (
                        f"Paper [{i+1}]: {title}\n"
                        f"  * Authors: {author_str or 'Unknown'}\n"
                        f"  * Published: {pub_date}\n"
                        f"  * ArXiv Link: {paper_url}\n"
                        f"  * Direct PDF: {pdf_url}.pdf\n"
                        f"  * Abstract: {summary[:450]}..."
                    )
                    summaries.append(paper_block)

                header = f"=== arXiv Academic Papers for '{topic}' ==="
                full_text = header + "\n\n" + "\n\n".join(summaries)
                return _to_ascii_safe(full_text)
        except Exception as e:
            logger.error(f"[WebResearchPlugin] arXiv query error: {e}")
            return f"Failed to query arXiv for '{topic}': {e}"

    # Backward-compatible method aliases
    search_web = web_search
    search_arxiv = search_academic_papers
