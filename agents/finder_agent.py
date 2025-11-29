"""
Paper Finder Agent - Searches for related academic papers using Tavily + arXiv
"""
import os
import json
import asyncio
import time
import re
import requests
import xml.etree.ElementTree as ET
from tavily import TavilyClient

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner


def tavily_search(query: str, max_results: int = 8):
    """Searches the web using Tavily and returns academic/technical links."""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("Warning: TAVILY_API_KEY not set")
            return []
        
        tavily_client = TavilyClient(api_key=api_key)
        # We use "advanced" depth to get better content
        results = tavily_client.search(query=query, max_results=max_results, search_depth="advanced")
        
        output = []
        for item in results.get("results", []):
            output.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "snippet": item.get("content", "")[:500] if item.get("content") else ""
            })
        return output
    except Exception as e:
        print(f"Tavily search error: {e}")
        return []



class PaperFinderAgent:
    def __init__(self):
        # We keep the agent definition just in case we need LLM filtering later, 
        # but for now we will use direct tool calls for reliability.
        self.agent = LlmAgent(
            name="paper_finder_agent",
            model=Gemini(model="gemini-2.5-flash-lite"),
            description="Finds academic papers using Tavily search.",
            instruction="You are a helper.", # Not used in direct mode
            tools=[tavily_search],
        )
        # self.runner will be initialized in the async method if needed
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "PaperReviewer/1.0"})
        self.arxiv_base_url = "https://export.arxiv.org/api/query"

    def _sanitize_query(self, query: str, max_words: int = 12) -> str:
        if not query:
            return "research paper"
        words = [w for w in re.findall(r"[A-Za-z0-9]+", query)]
        if not words:
            return "research paper"
        return " ".join(words[:max_words])

    def _arxiv_search(self, sanitized_query: str, max_results: int = 5) -> list:
        if not sanitized_query:
            sanitized_query = "research paper"
        params = {
            "search_query": f"all:{sanitized_query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        try:
            resp = self._session.get(self.arxiv_base_url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"⚠️ arXiv request failed: {exc}")
            return []

        try:
            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = []
            for entry in root.findall("atom:entry", ns):
                title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
                summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
                url_abs = entry.findtext("atom:id", default="", namespaces=ns) or ""
                published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:10]
                entries.append({
                    "title": title,
                    "url": url_abs,
                    "content": summary,
                    "snippet": summary[:500],
                    "published": published,
                    "source": "arxiv"
                })
            print(f"✅ arXiv returned {len(entries)} results")
            return entries
        except ET.ParseError as exc:
            print(f"⚠️ arXiv parse error: {exc}")
            return []
    
    async def find_papers_async(self, query: str, max_results: int = 10) -> list:
        """
        Find related academic papers (Async)
        """
        # Initialize runner here if we were using it (currently using direct tool call)
        # runner = InMemoryRunner(agent=self.agent)
        try:
            print(f"\n{'='*60}")
            print(f"🔎 PAPER FINDER AGENT - Starting paper search (Tavily + arXiv)")
            print(f"{'='*60}")
            print(f"❓ Query: {query}")
            
            # 1. Direct Tool Call (No LLM hallucination risk) - Tavily
            raw_papers = tavily_search(query, max_results=max_results)
            
            print(f"✅ Tavily returned {len(raw_papers)} results")
            
            # 2. Python-based Filtering for Academic Sources
            # This is more reliable than asking LLM to filter JSON
            academic_domains = [
                'arxiv.org', 'ieee.org', 'acm.org', 'springer.com', 
                'elsevier.com', 'nature.com', 'science.org', 'sciencedirect.com',
                'researchgate.net', 'semanticscholar.org', 'scholar.google.com',
                'mdpi.com', 'frontiersin.org', 'plos.org', 'wiley.com',
                'tandfonline.com', 'sagepub.com', 'hindawi.com', 'mdpi.com'
            ]
            
            filtered_papers = []
            for p in raw_papers:
                url = p.get('url', '').lower()
                # If it matches a domain OR if it looks like a PDF
                if any(d in url for d in academic_domains) or url.endswith('.pdf'):
                    filtered_papers.append({
                        **p,
                        'source': p.get('source', 'tavily')
                    })
                else:
                    # Keep it if it looks really relevant (fallback)
                    # For now, let's be permissive if we have few results
                    if len(raw_papers) < 3:
                        filtered_papers.append({
                            **p,
                            'source': p.get('source', 'tavily')
                        })

            # If we filtered too aggressively, revert to raw
            if not filtered_papers and raw_papers:
                print("⚠️  No strict academic domains found, using all results.")
                filtered_papers = [{**p, 'source': p.get('source', 'tavily')} for p in raw_papers]
            
            search_query = self._sanitize_query(query)
            arxiv_results = self._arxiv_search(search_query, max_results=min(5, max_results))
            combined = filtered_papers + arxiv_results

            # Deduplicate by URL/title combo
            deduped = []
            seen = set()
            for paper in combined:
                key = (paper.get('url') or paper.get('title', '')).lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(paper)
            
            print(f"✅ Returning {len(deduped)} total papers after merging sources")
            
            return deduped
            
        except Exception as e:
            print(f"❌ FINDER AGENT - Error: {str(e)}")
            return []

    def find_papers(self, query: str, max_results: int = 10) -> list:
        """Synchronous wrapper"""
        return asyncio.run(self.find_papers_async(query, max_results))
