"""
Parser Agent - Converts PDF to markdown and extracts metadata
"""
import asyncio
import json
import re
from typing import Dict, Any
from markitdown import MarkItDown
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner

class ParserAgent:
    def __init__(self):
        # Cache immutable agent configuration so we can build fresh agents per request
        self._agent_config = {
            "name": "pdf_metadata_extractor",
            "model_name": "gemini-2.5-flash-lite",
            "description": "Extracts structured metadata (Title, Abstract, etc.) from paper text.",
            "instruction": (
                "You are a Metadata Extractor.\n"
                "You will receive the first part of a research paper (in Markdown).\n"
                "Your job is to extract:\n"
                "1. Title\n"
                "2. Abstract (full text of the abstract)\n"
                "3. Authors (list of strings)\n"
                "4. Keywords (list of strings)\n\n"
                "Return a JSON object:\n"
                "{\n"
                "  'title': str,\n"
                "  'abstract': str,\n"
                "  'authors': [str, ...],\n"
                "  'keywords': [str, ...]\n"
                "}\n"
                "If a field is missing, use empty string/list."
            )
        }
        # runner will be created on-demand with a new agent so we never reuse closed event loops

    def _build_runner(self) -> InMemoryRunner:
        """Create a fresh runner each time to avoid reusing closed event loops."""
        agent = LlmAgent(
            name=self._agent_config["name"],
            model=Gemini(model=self._agent_config["model_name"]),
            description=self._agent_config["description"],
            instruction=self._agent_config["instruction"],
            tools=[],  # No tools needed, just text processing
        )
        return InMemoryRunner(agent=agent)
    
    async def parse_pdf_async(self, pdf_path: str) -> dict:
        """
        Parse PDF to markdown and extract metadata (Async)
        """
        # Initialize runner here to ensure it uses the current async loop
        runner = self._build_runner()
        try:
            print(f"\n{'='*60}")
            print(f"🔍 PARSER AGENT - Starting PDF parsing")
            print(f"{'='*60}")
            print(f"📄 File: {pdf_path}")
            
            # 1. Deterministic Parsing with MarkItDown
            md = MarkItDown()
            result = md.convert(pdf_path)
            full_text = result.text_content
            
            if not full_text:
                print("❌ PARSER AGENT - Failed to convert PDF to markdown (empty result)")
                return {'error': 'Empty result from MarkItDown'}
                
            print(f"✅ PDF converted to Markdown ({len(full_text)} chars)")
            
            # 2. LLM Metadata Extraction
            # We send the first 10k chars which usually covers Title, Abstract, Intro
            prompt_text = full_text[:10000]
            prompt = (
                "Here is the beginning of a research paper:\n"
                "========================================\n"
                f"{prompt_text}\n"
                "========================================\n"
                "Extract the metadata as JSON."
            )
            
            print(f"🔍 Extracting metadata with LLM...")
            response_list = await runner.run_debug(prompt)
            
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
            
            if not final_text:
                print("⚠️ PARSER AGENT - No response from LLM for metadata. Using basic fallback.")
                metadata = {}
            else:
                # Parse JSON
                try:
                    if "```json" in final_text:
                        final_text = final_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in final_text:
                        final_text = final_text.split("```")[1].split("```")[0].strip()
                    
                    metadata = json.loads(final_text)
                    print("✅ Metadata extracted successfully")
                except Exception as e:
                    print(f"⚠️ PARSER AGENT - JSON parsing failed: {e}. Using raw text fallback.")
                    metadata = {}

            # 3. Construct Final Result
            # Ensure we have at least a title from metadata or fallback
            if not metadata.get('title'):
                # Simple fallback: first non-empty line
                lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                metadata['title'] = lines[0] if lines else "Unknown Title"
                
            if not metadata.get('abstract'):
                metadata['abstract'] = "Abstract not found."

            # Combine
            return {
                'markdown': full_text,
                'full_content': full_text, # Alias
                'title': metadata.get('title'),
                'abstract': metadata.get('abstract'),
                'authors': metadata.get('authors', []),
                'keywords': metadata.get('keywords', []),
                'metadata': getattr(result, "metadata", {})
            }
            
        except Exception as e:
            print(f"❌ PARSER AGENT - Error: {str(e)}")
            return {'error': f'PDF parsing failed: {str(e)}'}

    def parse_pdf(self, pdf_path: str) -> dict:
        """Synchronous wrapper for parse_pdf_async"""
        return asyncio.run(self.parse_pdf_async(pdf_path))
