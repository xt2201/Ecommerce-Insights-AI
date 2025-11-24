import sys
import os
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_server.core.config import load_config
from ai_server.agents.market_agent import MarketAgent
from ai_server.agents.price_agent import PriceAgent

# Load environment variables
load_dotenv()
load_config()

def test_intelligence_agents():
    print("🚀 Testing Intelligence Agents...")
    
    # Mock products
    products = [
        {"title": "Sony WH-1000XM5", "price": 348.00, "rating": 4.5, "brand": "Sony", "asin": "B09XS7JWHH"},
        {"title": "Bose QuietComfort 45", "price": 279.00, "rating": 4.6, "brand": "Bose", "asin": "B098FKXT8L"},
        {"title": "Apple AirPods Max", "price": 479.00, "rating": 4.4, "brand": "Apple", "asin": "B08PZHYWJS"},
    ]
    
    # Test Market Agent
    print("\n📊 Testing Market Agent...")
    try:
        market_agent = MarketAgent()
        analysis, usage = market_agent.analyze_market_trends("noise cancelling headphones", products)
        print("✅ Market Analysis Success:")
        print(f"   - Segment: {analysis.market_segment}")
        print(f"   - Recommendation: {analysis.recommendation_strategy}")
    except Exception as e:
        print(f"❌ Market Agent Failed: {e}")
        import traceback
        traceback.print_exc()

    # Test Price Agent
    print("\n💰 Testing Price Agent...")
    try:
        price_agent = PriceAgent()
        analysis, usage = price_agent.analyze_price("Sony WH-1000XM5", 348.00)
        print("✅ Price Analysis Success:")
        print(f"   - Status: {analysis.price_status}")
        print(f"   - Recommendation: {analysis.recommendation}")
    except Exception as e:
        print(f"❌ Price Agent Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intelligence_agents()
