"""
Web Search - Search the web for current information
"""

import os
import aiohttp
from typing import List, Dict
from urllib.parse import quote_plus
import json


class WebSearch:
    """Handles web search functionality"""
    
    def __init__(self):
        """Initialize web search"""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CX")
        self.use_google = bool(self.google_api_key and self.google_cx)
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results with 'title', 'url', and 'snippet'
        """
        if self.use_google:
            return await self._google_search(query, num_results)
        else:
            return await self._duckduckgo_search(query, num_results)
    
    async def _google_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using Google Custom Search API"""
        try:
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cx,
                "q": query,
                "num": min(num_results, 10)  # Google API limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    
                    results = []
                    if "items" in data:
                        for item in data["items"][:num_results]:
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "snippet": item.get("snippet", "")
                            })
                    
                    return results
        except Exception as e:
            return [{"error": f"Search error: {str(e)}"}]
    
    async def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo (no API key required)"""
        try:
            # Use DuckDuckGo HTML search
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }) as resp:
                    html = await resp.text()
                    
                    # Simple parsing (for production, use BeautifulSoup)
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    result_divs = soup.find_all("div", class_="result")[:num_results]
                    
                    for div in result_divs:
                        title_elem = div.find("a", class_="result__a")
                        snippet_elem = div.find("a", class_="result__snippet")
                        
                        if title_elem:
                            results.append({
                                "title": title_elem.get_text(strip=True),
                                "url": title_elem.get("href", ""),
                                "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                            })
                    
                    return results if results else [{"error": "No results found"}]
        except Exception as e:
            return [{"error": f"Search error: {str(e)}"}]
    
    async def search_and_summarize(self, query: str, api_handler) -> str:
        """
        Search the web and get AI summary
        
        Args:
            query: Search query
            api_handler: API handler instance for AI summarization
            
        Returns:
            Summarized search results
        """
        results = await self.search(query, num_results=5)
        
        if not results or "error" in results[0]:
            return f"I couldn't find information about '{query}'. Please try a different search term."
        
        # Format results for AI
        formatted_results = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['snippet']}"
            for r in results
        ])
        
        prompt = f"""Based on these search results, provide a comprehensive answer to: {query}

Search Results:
{formatted_results}

Please provide a well-structured answer based on the search results above."""
        
        try:
            response = await api_handler.generate_response(
                messages=[{"role": "user", "content": prompt}],
                personality="helpful"
            )
            return response
        except Exception as e:
            # Fallback to simple formatting
            result_text = "\n\n".join([
                f"**{r['title']}**\n{r['snippet']}\n{r['url']}"
                for r in results[:3]
            ])
            return f"Here's what I found about '{query}':\n\n{result_text}"

