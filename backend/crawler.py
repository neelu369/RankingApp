"""
Web Crawler using Crawl4AI for gathering ranking data
"""
import sys
import asyncio

# FIX for Windows Playwright async issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import List, Dict, Any, Optional
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from bs4 import BeautifulSoup
import json
from config.settings import settings


class RankingCrawler:
    """Web crawler for gathering ranking-related data"""
    
    def __init__(self):
        self.max_pages = settings.crawl4ai_max_pages
        self.timeout = settings.crawl4ai_timeout
        
    async def crawl_url(self, url: str, extraction_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Crawl a single URL and extract structured data
        
        Args:
            url: URL to crawl
            extraction_prompt: Optional LLM prompt for structured extraction
            
        Returns:
            Dict containing crawled data
        """
        try:
            # Use simpler crawling without Playwright for Windows
            import httpx
            from bs4 import BeautifulSoup
            
            print(f"Crawling (simple mode): {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract text content
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            return {
                "url": url,
                "success": True,
                "html": html,
                "cleaned_html": html,
                "markdown": text[:5000],  # Limit to 5000 chars
                "extracted_content": None,
                "metadata": {
                    "title": soup.find('title').text if soup.find('title') else "",
                    "links": [a.get('href') for a in soup.find_all('a', href=True)][:50]
                }
            }
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    async def crawl_multiple(self, urls: List[str], extraction_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs concurrently
        
        Args:
            urls: List of URLs to crawl
            extraction_prompt: Optional extraction prompt
            
        Returns:
            List of crawled data
        """
        tasks = [self.crawl_url(url, extraction_prompt) for url in urls[:self.max_pages]]
        results = await asyncio.gather(*tasks)
        return results
    
    async def search_and_crawl(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for a query and crawl the results
        
        Args:
            query: Search query
            num_results: Number of results to crawl
            
        Returns:
            List of crawled data
        """
        search_urls = await self._get_search_results(query, num_results)
        return await self.crawl_multiple(search_urls)
    
    async def _get_search_results(self, query: str, num_results: int) -> List[str]:
        """Get search results URLs (using DuckDuckGo)"""
        try:
            import httpx
            from bs4 import BeautifulSoup

            search_url = 'https://html.duckduckgo.com/html/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; RankingApp/1.0)'
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(search_url, data={'q': query}, headers=headers)
                text = resp.text

            soup = BeautifulSoup(text, 'html.parser')

            urls: List[str] = []
            anchors = soup.find_all('a', class_='result__a') or soup.find_all('a')

            for a in anchors:
                href = a.get('href')
                if not href:
                    continue
                if href.startswith('http'):
                    urls.append(href)
                if len(urls) >= num_results:
                    break

            print(f"Found {len(urls)} search results for '{query}'")
            return urls[:num_results]
        except Exception as e:
            print(f"Error fetching search results for '{query}': {e}")
            return []
    
    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('title')
            return title.text if title else ""
        except:
            return ""
    
    async def crawl_for_metrics(self, entity_name: str, metric_name: str, sources: List[str]) -> Dict[str, Any]:
        """
        Crawl specific sources to find metric values for an entity
        
        Args:
            entity_name: Name of the entity
            metric_name: Metric to find
            sources: List of source URLs
            
        Returns:
            Dict containing found metric data
        """
        results = await self.crawl_multiple(sources[:3])  # Limit to 3 sources
        
        # Parse and aggregate results
        metric_data = {
            "entity": entity_name,
            "metric": metric_name,
            "values": [],
            "sources": []
        }
        
        for result in results:
            if result.get("success"):
                # Simple text extraction
                content = result.get("markdown", "")
                # Look for the metric in the content
                if metric_name.lower() in content.lower():
                    metric_data["values"].append({"value": "Found", "source_text": content[:200]})
                    metric_data["sources"].append(result["url"])
        
        return metric_data


# Global instance
crawler = RankingCrawler()