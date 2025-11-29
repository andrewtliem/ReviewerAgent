"""
Root Agent - Orchestrates the entire paper review workflow
"""
import os
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from .parser_agent import ParserAgent
from .finder_agent import PaperFinderAgent
from .ranking_agent import RankingAgent
from .reviewer_agent import ReviewerAgent
from .validator_agent import PaperValidationAgent


class RootAgent:
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.finder_agent = PaperFinderAgent()
        self.ranking_agent = RankingAgent()
        self.reviewer_agent = ReviewerAgent()
        self.validation_agent = PaperValidationAgent()
        
        # Create root orchestrator agent
        self.agent = LlmAgent(
            name="root_orchestrator",
            model=Gemini(model="gemini-2.5-flash"),
            description="Root orchestrator for the paper review system",
            instruction=(
                "You are the Root Orchestrator Agent for an academic paper review system.\n"
                "Your role is to coordinate the workflow:\n"
                "1. Receive parsed paper content (title, abstract, full text)\n"
                "2. Coordinate with other agents to find and rank related papers\n"
                "3. Coordinate comprehensive review generation\n"
                "4. Format final output as structured JSON\n\n"
                "Always maintain context and ensure smooth handoffs between agents.\n"
                "Provide clear, actionable instructions to each agent."
            ),
            tools=[]
        )
    
    def process_paper(self, file_path: str) -> dict:
        """
        Process a paper through the complete review pipeline
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Complete review result as dictionary
        """
        try:
            print("\n" + "="*80)
            print("🚀 ROOT AGENT - Starting Complete Review Pipeline")
            print("="*80)
            print(f"📁 Input File: {file_path}")
            print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Step 1: Parse the paper
            print("\n" + "─"*80)
            print("📝 STEP 1/5: PARSING PDF DOCUMENT")
            print("─"*80)
            parsed_data = self.parser_agent.parse_pdf(file_path)
            
            if not parsed_data or 'error' in parsed_data:
                print("❌ ROOT AGENT - Pipeline failed at parsing stage")
                return {
                    'error': 'Failed to parse PDF',
                    'details': parsed_data.get('error', 'Unknown error')
                }
            
            title = parsed_data.get('title', 'Unknown Title')
            abstract = parsed_data.get('abstract', '')
            
            print(f"✅ Step 1 Complete - Paper parsed successfully")
            print(f"   📄 Title: {title[:80]}...")
            print(f"   📋 Abstract: {len(abstract)} characters")
            
            # Step 2: Validate document authenticity
            print("\n" + "─"*80)
            print("🛡️  STEP 2/5: VALIDATING DOCUMENT TYPE")
            print("─"*80)
            validation = self.validation_agent.validate_document(
                paper_text=parsed_data.get('full_content', ''),
                metadata={'title': title, 'abstract': abstract}
            )

            if validation.get('error'):
                print(f"❌ ROOT AGENT - Validation failed: {validation['error']}")
                return {
                    'error': 'Failed to validate uploaded document',
                    'details': validation['error']
                }

            if not validation.get('is_research_paper'):
                print("⚠️ ROOT AGENT - Uploaded file rejected: not a research paper")
                return {
                    'error': 'Uploaded file does not appear to be a research paper',
                    'validation': validation
                }

            print(f"✅ Step 2 Complete - Document classified as research paper ({validation.get('confidence', 'Unknown')} confidence)")
            
            # Step 3: Find related papers
            print("\n" + "─"*80)
            print("📝 STEP 3/5: FINDING RELATED ACADEMIC PAPERS")
            print("─"*80)
            search_query = f"{title} {abstract[:200]}"
            print(f"🔍 Search strategy: Using title + first 200 chars of abstract")
            papers = self.finder_agent.find_papers(search_query)
            
            if not papers or len(papers) == 0:
                print("❌ ROOT AGENT - Pipeline failed: No related papers found")
                return {
                    'error': 'No related papers found',
                    'parsed_data': parsed_data
                }
            
            print(f"✅ Step 3 Complete - Found {len(papers)} related papers")
            
            # Step 4: Rank papers
            print("\n" + "─"*80)
            print("📝 STEP 4/5: RANKING RELATED PAPERS")
            print("─"*80)
            print(f"🎯 Ranking {len(papers)} papers to select top 5...")
            ranked_papers = self.ranking_agent.rank_papers(
                user_query=title,
                papers=papers,
                top_n=5
            )
            
            if not ranked_papers or len(ranked_papers) == 0:
                print("❌ ROOT AGENT - Pipeline failed at ranking stage")
                return {
                    'error': 'Failed to rank papers',
                    'papers': papers
                }
            
            print(f"✅ Step 4 Complete - Ranked top {len(ranked_papers)} papers")
            
            # Step 5: Generate review
            print("\n" + "─"*80)
            print("📝 STEP 5/5: GENERATING COMPREHENSIVE REVIEW")
            print("─"*80)
            print(f"📊 Comparing uploaded paper with {len(ranked_papers)} top-ranked papers")
            print(f"🤖 Review Agent will analyze:")
            print(f"   ✓ Original paper (title, abstract, content)")
            print(f"   ✓ Top {len(ranked_papers)} related papers for context")
            print(f"   ✓ Relative positioning in the research landscape")
            
            review = self.reviewer_agent.generate_review(
                paper_data=parsed_data,
                related_papers=ranked_papers
            )
            
            if not review or 'error' in review:
                print("❌ ROOT AGENT - Pipeline failed at review generation stage")
                return {
                    'error': 'Failed to generate review',
                    'details': review.get('error', 'Unknown error')
                }
            
            print(f"✅ Step 5 Complete - Review generated successfully")
            
            # Final Step: Format final output
            print("\n" + "─"*80)
            print("📝 FINAL STEP: FORMATTING OUTPUT")
            print("─"*80)
            
            final_result = {
                'paper': {
                    'title': title,
                    'abstract': abstract,
                    'authors': parsed_data.get('authors', []),
                    'keywords': parsed_data.get('keywords', [])
                },
                'related_papers': ranked_papers,
                'review': review,
                'metadata': {
                    'validation': validation,
                    'total_papers_found': len(papers),
                    'papers_ranked': len(ranked_papers),
                    'review_generated_at': review.get('generated_at', '')
                }
            }
            
            print(f"\n{'='*80}")
            print(f"🎉 ROOT AGENT - PIPELINE COMPLETE!")
            print(f"{'='*80}")
            print(f"📊 Final Output Summary:")
            print(f"   ✓ Paper analyzed: {title[:60]}...")
            print(f"   ✓ Related papers included: {len(ranked_papers)}")
            print(f"   ✓ Review summary: {review.get('summary', '')[:60]}...")
            overall = review.get('overall_assessment', {})
            if isinstance(overall, dict):
                print(f"   ✓ Recommendation: {overall.get('recommendation', 'N/A')}")
            else:
                print(f"   ✓ Overall assessment: {str(overall)[:60]}...")
            print(f"⏰ End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}\n")
            
            return final_result
        
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ ROOT AGENT - CRITICAL ERROR")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            print(f"{'='*80}\n")
            return {
                'error': 'Root agent processing failed',
                'details': str(e)
            }
