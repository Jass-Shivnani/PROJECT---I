"""
Dione AI — Web Research & Scraping Plugin
=========================================
Provides real-time web search, URL content scraping, and academic research synthesis
using HTTP requests with automatic HTML parsing and sanitization.
"""

import re
import html
from html.parser import HTMLParser
from typing import Optional
from loguru import logger
import httpx

from server.plugins.base import BasePlugin, dione_tool


class HTMLTextExtractor(HTMLParser):
    """Clean HTML text extractor that removes scripts, styles, and extracts readable text."""
    
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_tags = {"script", "style", "nav", "header", "footer", "noscript"}
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
    """Web search, content scraping, and academic paper extraction."""
    
    name = "WebResearchPlugin"
    description = "Search the live web, scrape web pages, and look up academic papers"
    version = "0.2.0"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    @dione_tool(
        description="Search the web for current information, facts, or technical topics",
        permission_level="read"
    )
    async def web_search(self, query: str, max_results: int = 5) -> str:
        """Search the web and return top result snippets with source links.
        
        :param query: The search query string
        :param max_results: Maximum number of results to return (default 5)
        """
        logger.info(f"🔎 Web search query: {query}")
        results = []

        try:
            # 1. First attempt DuckDuckGo instant answer / search
            async with httpx.AsyncClient(timeout=10.0, headers=self.HEADERS, follow_redirects=True) as client:
                # DuckDuckGo HTML Lite search
                url = "https://html.duckduckgo.com/html/"
                resp = await client.post(url, data={"q": query})
                
                if resp.status_code == 200:
                    # Parse results from DuckDuckGo HTML
                    text = resp.text
                    # Extract result snippets
                    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', text, re.DOTALL)
                    titles = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', text, re.DOTALL)
                    
                    for i in range(min(len(snippets), max_results)):
                        clean_snippet = re.sub(r'<[^>]+>', '', html.unescape(snippets[i])).strip()
                        clean_url = re.sub(r'<[^>]+>', '', html.unescape(titles[i] if i < len(titles) else "")).strip()
                        if clean_snippet:
                            results.append(f"[{i+1}] {clean_snippet} (Source: {clean_url or 'DuckDuckGo'})")

        except Exception as e:
            logger.debug(f"DuckDuckGo search fallback: {e}")

        # 2. Fallback / supplementary Wikipedia API lookup for conceptual queries
        if not results or len(results) < 2:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
                    wiki_resp = await client.get(wiki_url)
                    if wiki_resp.status_code == 200:
                        data = wiki_resp.json()
                        extract = data.get("extract", "")
                        title = data.get("title", query)
                        source_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                        if extract:
                            results.insert(0, f"[Wikipedia] {title}: {extract} (Source: {source_url})")
            except Exception as e:
                logger.debug(f"Wikipedia fallback failed: {e}")

        if results:
            return "\n\n".join(results[:max_results])
        return f"No search results found for '{query}'. Try refining the search terms."

    @dione_tool(
        description="Scrape and extract clean readable text content from any public webpage or URL",
        permission_level="read"
    )
    async def scrape_url(self, url: str, max_chars: int = 2500) -> str:
        """Fetch and extract readable text from a URL.
        
        :param url: The web page URL to scrape (e.g. 'https://en.wikipedia.org/wiki/Artificial_intelligence')
        :param max_chars: Maximum characters of text to return (default 2500)
        """
        logger.info(f"🌐 Scraping URL: {url}")
        
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(timeout=12.0, headers=self.HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return f"HTTP error {resp.status_code} while fetching {url}"
                
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    return resp.text[:max_chars]

                parser = HTMLTextExtractor()
                parser.feed(resp.text)
                extracted_text = parser.get_text()

                # Clean multiple whitespaces
                extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
                title_prefix = f"Page Title: {parser.title}\nURL: {url}\n\n" if parser.title else f"URL: {url}\n\n"
                
                if not extracted_text:
                    return f"Successfully fetched {url}, but could not find readable textual content."

                return title_prefix + extracted_text[:max_chars]
        except httpx.TimeoutException:
            return f"Timeout occurred while connecting to {url}. The server took longer than 12 seconds to respond."
        except Exception as e:
            return f"Failed to scrape {url}: {str(e)}"

    @dione_tool(
        description="Search for arXiv academic research papers by topic or keyword",
        permission_level="read"
    )
    async def search_academic_papers(self, topic: str, max_results: int = 3) -> str:
        """Search arXiv.org for academic computer science research papers and extract abstract summaries.
        
        :param topic: Research topic or title keywords (e.g. 'Large Action Models')
        :param max_results: Number of papers to fetch (default 3)
        """
        logger.info(f"📚 Searching arXiv academic papers for: {topic}")
        clean_topic = re.sub(r'[^\w\s]', '', topic).replace(' ', '+')
        api_url = f"http://export.arxiv.org/api/query?search_query=all:{clean_topic}&start=0&max_results={max_results}"

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(api_url)
                if resp.status_code != 200:
                    return f"arXiv API returned status {resp.status_code}"
                
                xml_text = resp.text
                entries = re.findall(r'<entry>(.*?)</entry>', xml_text, re.DOTALL)
                if not entries:
                    return f"No academic papers found on arXiv for topic '{topic}'."

                summaries = []
                for i, entry in enumerate(entries[:max_results]):
                    title_m = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    summary_m = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    id_m = re.search(r'<id>(.*?)</id>', entry, re.DOTALL)
                    
                    title = re.sub(r'\s+', ' ', title_m.group(1)).strip() if title_m else "Unknown Title"
                    summary = re.sub(r'\s+', ' ', summary_m.group(1)).strip() if summary_m else "No abstract available."
                    paper_url = id_m.group(1).strip() if id_m else ""
                    
                    summaries.append(f"📄 Paper [{i+1}]: {title}\nLink: {paper_url}\nAbstract: {summary[:400]}...")

                return "\n\n".join(summaries)
        except Exception as e:
            return f"Failed to query arXiv for '{topic}': {str(e)}"
