"""
Validation Agent - Determines if uploaded content is a research paper
"""
import asyncio
import json
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner


class PaperValidationAgent:
    def __init__(self):
        self._agent_config = {
            "name": "paper_validation_agent",
            "model_name": "gemini-2.5-flash-lite",
            "description": "Classifies whether parsed PDF text is a legitimate academic paper.",
            "instruction": (
                "You are a PDF validation agent. Determine if the provided text "
                "represents an academic/research paper (e.g., conference or journal article). "
                "Consider structure (title, abstract, sections, references), terminology, "
                "and presence of research artifacts (methods, experiments, citations).\n\n"
                "Classify into one of three categories:\n"
                "1. research_paper – Scholarly work with research content.\n"
                "2. non_academic_document – General reports, slides, invoices, books, etc.\n"
                "3. unclear – Not enough information to decide.\n\n"
                "Return valid JSON:\n"
                "{\n"
                "  'is_research_paper': bool,\n"
                "  'category': 'research_paper' | 'non_academic_document' | 'unclear',\n"
                "  'confidence': 'High' | 'Medium' | 'Low',\n"
                "  'reason': 'Short explanation referencing evidence from the text'\n"
                "}\n"
                "Be strict: marketing brochures, resumes, or blank documents are not research papers."
            ),
        }

    def _build_runner(self) -> InMemoryRunner:
        agent = LlmAgent(
            name=self._agent_config["name"],
            model=Gemini(model=self._agent_config["model_name"]),
            description=self._agent_config["description"],
            instruction=self._agent_config["instruction"],
            tools=[],
        )
        return InMemoryRunner(agent=agent)

    async def validate_document_async(self, *, paper_text: str, metadata: dict | None = None) -> dict:
        """Run validation asynchronously."""
        runner = self._build_runner()
        metadata = metadata or {}
        title = metadata.get("title", "Unknown Title")
        abstract = metadata.get("abstract", "") or "No abstract provided."
        # Clamp text to avoid overly long prompts
        sample_text = (paper_text or "")[:20000]
        prompt = (
            f"Title: {title}\n"
            f"Abstract: {abstract}\n\n"
            "PDF Content Sample:\n"
            "----- START OF SAMPLE -----\n"
            f"{sample_text}\n"
            "----- END OF SAMPLE -----\n\n"
            "Decide if this is a legitimate research paper following the instructions."
        )
        try:
            response_list = await runner.run_debug(prompt)
            final_text = ""
            for item in reversed(response_list):
                if hasattr(item, "content") and item.content and item.content.parts:
                    for part in item.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text = part.text
                            break
                if final_text:
                    break

            if not final_text:
                return {"error": "No response from validation agent"}

            # Extract JSON payload
            if "```json" in final_text:
                final_text = final_text.split("```json")[1].split("```")[0].strip()
            elif "```" in final_text:
                final_text = final_text.split("```")[1].split("```")[0].strip()

            data = json.loads(final_text)
            return data

        except Exception as exc:
            return {"error": f"Validation failed: {str(exc)}"}

    def validate_document(self, *, paper_text: str, metadata: dict | None = None) -> dict:
        """Synchronous wrapper."""
        return asyncio.run(self.validate_document_async(paper_text=paper_text, metadata=metadata))
