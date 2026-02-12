#!/usr/bin/env python3
"""
Test script for the Ranking App
Tests basic functionality without requiring full setup
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from config.settings import settings
        print("✓ Config imported")
        
        from backend.ranking_engine import ranking_engine
        print("✓ Ranking engine imported")
        
        from backend.llm_interface import ReplicateLLM, ranking_llm
        print("✓ LLM interface imported")
        
        from backend.agent import RankingAgent
        print("✓ Agent imported")
        
        print("\n✓ All imports successful!")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_ranking_engine():
    """Test the ranking engine with sample data"""
    print("\nTesting ranking engine...")
    try:
        from backend.ranking_engine import ranking_engine
        
        # Sample entities
        entities = [
            {"name": "Entity A", "score": 85, "rating": 4.5},
            {"name": "Entity B", "score": 92, "rating": 4.8},
            {"name": "Entity C", "score": 78, "rating": 4.2},
        ]
        
        # Sample metrics
        metrics = [
            {"name": "score", "type": "numerical", "higher_is_better": True},
            {"name": "rating", "type": "numerical", "higher_is_better": True},
        ]
        
        # Rank
        results = ranking_engine.rank_entities(entities, metrics)
        
        print(f"Ranked {len(results)} entities:")
        for r in results:
            print(f"  Rank {r['rank']}: {r['name']} (score: {r['final_score']:.3f})")
        
        print("\n✓ Ranking engine works!")
        return True
    except Exception as e:
        print(f"\n✗ Ranking engine test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from config.settings import settings
        
        print(f"Replicate API Key: {'✓ Set' if settings.replicate_api_key else '✗ NOT SET'}")
        print(f"OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ NOT SET'}")
        print(f"MongoDB URI: {settings.mongodb_uri}")
        print(f"Default LLM Model: {settings.default_llm_model}")
        
        if not settings.replicate_api_key:
            print("\n⚠ WARNING: Replicate API key not set!")
            print("  Set REPLICATE_API_KEY in your .env file")
        
        return True
    except Exception as e:
        print(f"\n✗ Config test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("RANKING APP - TEST SUITE")
    print("="*60)
    
    tests = [
        test_imports,
        test_config,
        test_ranking_engine,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed! App is ready to run.")
        print("\nNext steps:")
        print("1. Ensure MongoDB is running")
        print("2. Set REPLICATE_API_KEY in .env")
        print("3. Run: python backend/main.py")
    else:
        print("\n✗ Some tests failed. Please fix the errors above.")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())