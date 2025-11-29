"""
Ranking Agent - Ranks papers by relevance and quality
"""
import json
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner

class RankingAgent:
    def __init__(self):
        self._agent_config = {
            "name": "paper_ranking_agent",
            "model_name": "gemini-2.5-flash-lite",
            "description": "Ranks papers from paper_finder_agent by relevance and quality.",
            "instruction": (
                "You are a Paper Ranking Agent.\n"
                "You receive:\n"
                "  1) the original user query, and\n"
                "  2) the JSON output from paper_finder_agent as plain text.\n\n"
                "The finder output is a JSON object like:\n"
                "{ 'papers': [ { 'title': ..., 'url': ..., 'snippet': ... , ... }, ... ] }\n\n"
                "Your tasks:\n"
                "1. Parse that JSON safely (ignore if it's slightly malformed and repair it).\n"
                "2. For each paper, assign:\n"
                "   - relevance_score: integer 1–10 (10 = perfectly on-topic).\n"
                "   - quality_score: integer 1–10 (10 = strong venue + recent + technical).\n"
                "   - reason: 1–3 sentences explaining your scores.\n"
                "3. Sort papers by relevance_score desc, then quality_score desc.\n\n"
                "OUTPUT STRICTLY as a JSON object:\n"
                "{\n"
                "  'ranked_papers': [\n"
                "    {\n"
                "      'rank': int,\n"
                "      'title': str,\n"
                "      'url': str,\n"
                "      'relevance_score': int,\n"
                "      'quality_score': int,\n"
                "      'reason': str,\n"
                "      'original': object  # original paper dict as received\n"
                "    }\n"
                "  ],\n"
                "  'notes': str\n"
                "}\n"
                "Do NOT invent new papers; only rank the ones provided."
            )
        }
        # runner will be created when ranking to avoid carrying event-loop-bound state

    def _build_runner(self) -> InMemoryRunner:
        agent = LlmAgent(
            name=self._agent_config["name"],
            model=Gemini(model=self._agent_config["model_name"]),
            description=self._agent_config["description"],
            instruction=self._agent_config["instruction"],
            tools=[],
            generate_content_config=None
        )
        return InMemoryRunner(agent=agent)
    
    async def rank_papers_async(self, user_query: str, papers: list, top_n: int = 5) -> list:
        """
        Rank papers by relevance and quality (Async)
        """
        # Initialize runner here to ensure it uses the current async loop
        runner = self._build_runner()
        if not papers:
            return []
            
        # Construct the prompt
        finder_output = json.dumps({"papers": papers}, indent=2)
        prompt = (
            f"User query:\n{user_query}\n\n"
            "Here is the JSON output from paper_finder_agent:\n"
            f"{finder_output}\n\n"
            "Please rank these papers as instructed."
        )
        
        try:
            print(f"\n{'='*60}")
            print(f"🏆 RANKING AGENT - Starting paper ranking (LLM-driven)")
            print(f"{'='*60}")
            
            response_list = await runner.run_debug(prompt)
            
            # Debug logging
            print(f"DEBUG: Received {len(response_list)} items in response_list")
            
            # Extract final text
            final_text = ""
            for item in reversed(response_list):
                if hasattr(item, "content") and item.content and item.content.parts:
                    part_text = ""
                    for part in item.content.parts:
                        if hasattr(part, "text") and part.text:
                            part_text += part.text
                    if part_text:
                        final_text = part_text
                        break
            
            print(f"DEBUG: Final text extracted: {final_text[:200]}...")
            
            if not final_text:
                print("❌ RANKING AGENT - No text response from LLM")
                return []

            # Parse JSON
            try:
                cleaned_text = final_text.replace('\xa0', ' ').strip()
                if "```json" in cleaned_text:
                    cleaned_text = cleaned_text.split("```json", 1)[1]
                    cleaned_text = cleaned_text.split("```", 1)[0].strip()
                elif "```" in cleaned_text:
                    cleaned_text = cleaned_text.split("```", 1)[1]
                    cleaned_text = cleaned_text.split("```", 1)[0].strip()
                else:
                    start = cleaned_text.find('{')
                    end = cleaned_text.rfind('}') + 1
                    if start != -1 and end > start:
                        cleaned_text = cleaned_text[start:end]
                cleaned_text = cleaned_text.rstrip(';').rstrip()

                data = json.loads(cleaned_text)
            except json.JSONDecodeError:
                print(f"❌ RANKING AGENT - Failed to parse JSON. Raw text: {final_text[:500]}")
                # Fallback
                import re
                import ast
                try:
                    match = re.search(r'\{.*\}', final_text, re.DOTALL)
                    if match:
                        data = ast.literal_eval(match.group(0))
                    else:
                        raise ValueError("No JSON object found")
                except Exception as e2:
                    print(f"❌ RANKING AGENT - JSON fallback failed: {str(e2)}")
                    return []
            
            ranked_papers = data.get('ranked_papers', [])
            
            # Return top N
            return ranked_papers[:top_n]
            
        except Exception as e:
            print(f"Error ranking papers: {str(e)}")
            return []

    def rank_papers(self, user_query: str, papers: list, top_n: int = 5) -> list:
        """Synchronous wrapper"""
        return asyncio.run(self.rank_papers_async(user_query, papers, top_n))
