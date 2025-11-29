"""
Test script to demonstrate the complete agent workflow with logging
Run this to see all agent outputs in action
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.root_agent import RootAgent

def main():
    """Test the paper review workflow"""
    
    print("\n" + "="*80)
    print("🧪 TESTING AI PAPER REVIEWER - AGENT WORKFLOW")
    print("="*80)
    print("\nThis test will show you the complete agent workflow with detailed logging.")
    print("You'll see how each agent processes the paper and passes data to the next.\n")
    
    # Check for API keys
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
        print("Please add your Google AI API key to the .env file\n")
        return
    
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ ERROR: TAVILY_API_KEY not found in .env file")
        print("Please add your Tavily API key to the .env file\n")
        return
    
    # Check for test PDF
    test_file = input("\n📄 Enter path to test PDF (or press Enter to skip): ").strip()
    
    if not test_file:
        print("\n⚠️  No test file provided. The workflow requires a PDF file to test.")
        print("\nTo test the system:")
        print("1. Add your API keys to .env file")
        print("2. Run: python app.py")  
        print("3. Upload a PDF through the web interface at http://localhost:5000")
        print("\nYou'll see all the agent logs in the terminal where app.py is running.\n")
        return
    
    if not os.path.exists(test_file):
        print(f"\n❌ ERROR: File not found: {test_file}\n")
        return
    
    # Initialize root agent
    print("\n🔧 Initializing agents...")
    root_agent = RootAgent()
    print("✅ All agents initialized\n")
    
    # Process the paper
    print("▶️  Starting paper review process...\n")
    print("─"*80)
    
    result = root_agent.process_paper(test_file)
    
    # Display results summary
    print("\n" + "="*80)
    print("📋 RESULTS SUMMARY")
    print("="*80)
    
    if 'error' in result:
        print(f"\n❌ Process failed: {result['error']}")
        if 'details' in result:
            print(f"   Details: {result['details']}")
    else:
        paper = result.get('paper', {})
        review = result.get('review', {})
        related = result.get('related_papers', [])
        
        print(f"\n✅ Review completed successfully!")
        print(f"\n📊 Paper Information:")
        print(f"   Title: {paper.get('title', 'N/A')}")
        print(f"   Authors: {len(paper.get('authors', []))} found")
        print(f"   Keywords: {len(paper.get('keywords', []))} found")
        
        print(f"\n📚 Related Papers: {len(related)} papers ranked")
        for i, p in enumerate(related, 1):
            print(f"   {i}. {p['title'][:60]}... [Score: {p['combined_score']}]")
        
        print(f"\n📝 Review Summary:")
        assessment = review.get('overall_assessment', {})
        print(f"   Recommendation: {assessment.get('recommendation', 'N/A')}")
        print(f"   Confidence: {assessment.get('confidence', 'N/A')}")
        print(f"   Strengths: {len(review.get('strengths', []))} points")
        print(f"   Weaknesses: {len(review.get('weaknesses', []))} points")
        print(f"   Questions: {len(review.get('questions', []))} questions")
    
    print("\n" + "="*80)
    print("🎉 TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
