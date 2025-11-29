"""
Reviewer Agent - Generates comprehensive paper reviews
"""
import json
import asyncio
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner


class ReviewerAgent:
    def __init__(self):
        self._agent_config = {
            "name": "assistant_reviewer_agent",
            "model_name": "gemini-2.5-flash-lite",
            "description": "Compares an uploaded paper against reference papers and produces a structured review.",
            "instruction": (
                "You are an Assistant Reviewer for research papers.\n\n"
                "INPUT YOU WILL RECEIVE (as plain text in the user message):\n"
                "1. The user's original research topic or question.\n"
                "2. The uploaded paper in Markdown format (produced by a parser agent).\n"
                "3. The JSON output from a ranking agent, containing at least the top 5 reference papers.\n"
                "   It looks like:\n"
                "   {\n"
                "     'ranked_papers': [\n"
                "       {\n"
                "         'rank': int,\n"
                "         'title': str,\n"
                "         'url': str,\n"
                "         'relevance_score': int,\n"
                "         'quality_score': int,\n"
                "         'reason': str,\n"
                "         'original': { ... }   # original paper dict from the finder agent\n"
                "       }, ...\n"
                "     ],\n"
                "     'notes': str\n"
                "   }\n\n"
                "YOUR JOB:\n"
                "1. Parse and understand the uploaded paper (Markdown).\n"
                "2. Read the TOP 5 ranked reference papers from the JSON (do not invent any new paper).\n"
                "3. Compare the uploaded paper against these references in terms of:\n"
                "   - Novelty (what is new or not new)\n"
                "   - Technical depth and correctness\n"
                "   - Methodology and experiments\n"
                "   - Clarity of writing and structure\n"
                "   - Positioning relative to existing work (is related work adequate?)\n\n"
                "4. Produce a structured review with the following sections:\n"
                "   - Strengths: 2–4 thematic blocks. Each block must start with a plain heading such as "
                "     'Technical novelty:' followed by multiple sentences that cite evidence from the manuscript "
                "     and explicitly compare against at least one ranked reference when relevant. Highlight impact, "
                "     methodological rigor, and clarity only if they truly exceed typical high-impact journal expectations.\n"
                "   - Weaknesses: mirror the strength format and be uncompromising—call out missing experiments, "
                "     reproducibility gaps, weak baselines, unclear writing, or overstated claims. Every weakness should "
                "     explain why it prevents acceptance at a high-impact venue.\n"
                "   - DetailedComments: Provide five subsections in this exact order— 'Title and Abstract', 'Introduction', "
                "     'Methodology', 'Experiments', 'Conclusion'. Each subsection must be a dense, evidence-based paragraph "
                "     (no bullets) enumerating concrete issues, improvement suggestions, and cross-references to the ranked papers.\n"
                "   - Questions: 3–5 precise questions the authors must answer before reconsideration; focus on missing data, "
                "     ablations, theoretical gaps, or unclear claims.\n"
                "   - OverallAssessment: provide recommendation, confidence, and a justification paragraph summarizing how "
                "     novelty, rigor, and positioning compare to the references. Recommendations should follow top-tier venues "
                "     (e.g., 'Strong Reject', 'Weak Reject', 'Borderline', 'Weak Accept', 'Strong Accept').\n\n"
                "OUTPUT FORMAT (VERY IMPORTANT):\n"
                "Return a single JSON object with this exact structure:\n"
                "{\n"
                "  'summary': str,\n"
                "  'strengths': [str, ...],\n"
                "  'weaknesses': [str, ...],\n"
                "  'detailed_comments': {\n"
                "    'Title and Abstract': str,\n"
                "    'Introduction': str,\n"
                "    'Methodology': str,\n"
                "    'Experiments': str,\n"
                "    'Conclusion': str\n"
                "  },\n"
                "  'questions': [str, ...],\n"
                "  'related_work_analysis': str,  # A specific paragraph analyzing how this paper compares to the reference papers\n"
                "  'overall_assessment': {\n"
                "    'recommendation': str,       # e.g., 'Strong Accept', 'Weak Accept', 'Reject'\n"
                "    'confidence': str,           # e.g., 'High', 'Medium', 'Low'\n"
                "    'justification': str         # The main text of the overall assessment\n"
                "  }\n"
                "}\n\n"
                "GUIDELINES:\n"
                "- Be honest but constructive.\n"
                "- Ground your comments in comparison with the 5 reference papers whenever possible.\n"
                "- Do NOT hallucinate specific equations or exact metrics if they are not in the text.\n"
                "- Do NOT fabricate new references beyond the provided ranked list.\n"
                "- Use polished academic prose suitable for an academic review.\n"
                "- When referencing related work, cite the ranked papers by brief title cues (e.g., 'the 2023 OCO-DBA paper').\n"
                "- Avoid generic praise; every bullet should contain evidence pulled from the manuscript or comparisons, and non-trivial criticism is expected.\n"
                "- Maintain a critical, professional tone consistent with reviewers for high-impact journals.\n"
                "- Do NOT use Markdown bold markers (**) or other formatting characters inside any section; rely on sentences with leading phrases for emphasis.\n"
            )
        }
        # runner will be built per review request

    def _build_runner(self) -> InMemoryRunner:
        agent = LlmAgent(
            name=self._agent_config["name"],
            model=Gemini(model=self._agent_config["model_name"]),
            description=self._agent_config["description"],
            instruction=self._agent_config["instruction"],
            tools=[]
        )
        return InMemoryRunner(agent=agent)
    
    async def generate_review_async(self, paper_data: dict, related_papers: list) -> dict:
        """
        Generate comprehensive review (Async)
        """
        # Initialize runner here to ensure it uses the current async loop
        runner = self._build_runner()
        try:
            print(f"\n{'='*60}")
            print(f"✍️  REVIEWER AGENT - Starting review generation (LLM-driven)")
            print(f"{'='*60}")
            
            # Prepare context
            title = paper_data.get('title', 'Unknown Title')
            abstract = paper_data.get('abstract', '')
            full_content = paper_data.get('full_content', '')
            
            # Format uploaded paper markdown
            uploaded_paper_md = f"# {title}\n\n## Abstract\n{abstract}\n\n## Content\n{full_content[:20000]}" # Truncate if too huge
            
            # Format ranked papers JSON
            ranked_papers_json = json.dumps({"ranked_papers": related_papers}, indent=2)
            
            prompt = (
                f"User Topic: {title}\n\n"
                "UPLOADED PAPER (Markdown):\n"
                f"{uploaded_paper_md}\n\n"
                "RANKED REFERENCE PAPERS (JSON):\n"
                f"{ranked_papers_json}\n\n"
                "Please generate the review as instructed."
            )
            
            response_list = await runner.run_debug(prompt)
            
            # Debug logging
            print(f"DEBUG: Received {len(response_list)} items in response_list")
            
            # Extract final text
            final_text = ""
            for item in reversed(response_list):
                if hasattr(item, "content") and item.content and item.content.parts:
                    for part in item.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text = part.text
                            break
                if final_text:
                    break
            
            print(f"DEBUG: Final text extracted: {final_text[:200]}...")
            
            if not final_text:
                print("❌ REVIEWER AGENT - No text response from LLM")
                return {'error': 'No response from LLM'}

            # Parse JSON
            try:
                final_text = final_text.replace('\xa0', ' ').strip()
                if "```json" in final_text:
                    final_text = final_text.split("```json", 1)[1]
                    final_text = final_text.split("```", 1)[0].strip()
                elif "```" in final_text:
                    final_text = final_text.split("```", 1)[1]
                    final_text = final_text.split("```", 1)[0].strip()
                else:
                    brace_start = final_text.find('{')
                    brace_end = final_text.rfind('}') + 1
                    if brace_start != -1 and brace_end > brace_start:
                        final_text = final_text[brace_start:brace_end]
                final_text = final_text.rstrip(';').rstrip()

                review = json.loads(final_text)
            except json.JSONDecodeError:
                print(f"❌ REVIEWER AGENT - Failed to parse JSON. Raw text: {final_text[:500]}")
                # Fallback
                import re
                import ast
                try:
                    match = re.search(r'\{.*\}', final_text, re.DOTALL)
                    if match:
                        review = ast.literal_eval(match.group(0))
                    else:
                        raise ValueError("No JSON object found")
                except Exception as e2:
                    return {'error': f'Failed to parse JSON response: {str(e2)}'}
            
            review['generated_at'] = datetime.now().isoformat()
            
            return review
            
        except Exception as e:
            print(f"❌ REVIEWER AGENT - Error: {str(e)}")
            return {'error': f'Review generation failed: {str(e)}'}

    def generate_review(self, paper_data: dict, related_papers: list) -> dict:
        """Synchronous wrapper"""
        return asyncio.run(self.generate_review_async(paper_data, related_papers))
