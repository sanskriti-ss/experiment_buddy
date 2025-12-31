#!/usr/bin/env python3
"""
Test script for the new review article detection and improved scoring
"""
import requests
import json

SERVER_URL = "http://localhost:8000"

def test_review_article_detection():
    """Test that review articles are properly detected"""
    review_text = """
    Microglia are the resident macrophages of the central nervous system (CNS), 
    and their functions are adapted to their location and their reciprocal 
    interactions with nearby cells and structures. In physiological conditions, 
    microglia play an important role in shaping neuronal ensembles and regulating 
    synaptic transmission. Moreover, microglia maintain the integrity of the CNS 
    through their ability to efficiently phagocytose synapses, soluble antigens, 
    debris, and apoptotic cells. Studies have shown that these cells are essential 
    for brain development and homeostasis. Recent research has demonstrated that 
    various protocols to generate MCCOs have been developed in the last few years 
    using different strategies.
    """
    
    payload = {
        "text": review_text,
        "source": "test",
        "model": "openai/gpt-4o-mini"
    }
    
    print("Testing review article detection...")
    response = requests.post(f"{SERVER_URL}/extract", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("Response:", json.dumps(data, indent=2))
        
        if not data.get("success") and data.get("error") == "review_article_detected":
            print("✅ Review article correctly detected!")
            print(f"   Reason: {data.get('message')}")
            print(f"   Suggestion: {data.get('suggestion')}")
            return True
        else:
            print("❌ Review article not detected when it should have been")
            return False
    else:
        print(f"❌ Request failed with status {response.status_code}")
        return False

def test_methods_section():
    """Test that actual methods are processed normally"""
    methods_text = """
    Cells were cultured in DMEM medium supplemented with 10% FBS at 37°C. 
    Cells were seeded at 50,000 cells per well in 24-well plates. 
    After 24 hours, cells were treated with 100 μM drug for 2 hours. 
    Cells were then washed twice with PBS and fixed with 4% paraformaldehyde 
    for 15 minutes at room temperature. Primary antibody was added at 1:1000 
    dilution and incubated overnight at 4°C.
    """
    
    payload = {
        "text": methods_text,
        "source": "test", 
        "model": "openai/gpt-4o-mini"
    }
    
    print("\nTesting actual methods section...")
    response = requests.post(f"{SERVER_URL}/extract", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            print("✅ Methods section processed successfully!")
            
            # Check the analysis results
            analysis = data.get("analysis", {})
            overall_score = analysis.get("overall_score", 0)
            print(f"   Overall score: {overall_score}")
            
            # Check individual steps for proper scoring
            steps = analysis.get("steps", [])
            for step in steps:
                print(f"   Step: {step.get('text', '')[:50]}...")
                print(f"     Action: {step.get('action')}")
                print(f"     Score: {step.get('completeness_score')}")
            
            return True
        else:
            print("❌ Methods section failed to process")
            print("Error:", data.get("error"))
            return False
    else:
        print(f"❌ Request failed with status {response.status_code}")
        return False

def test_non_procedural_scoring():
    """Test that non-procedural text gets low scores"""
    non_procedural_text = """
    This study demonstrates the importance of microglia in brain function. 
    These cells are known to be essential for maintaining neural health.
    Previous research has shown that dysfunction leads to neurodegeneration.
    """
    
    payload = {
        "text": non_procedural_text,
        "source": "test",
        "model": "openai/gpt-4o-mini"
    }
    
    print("\nTesting non-procedural text scoring...")
    response = requests.post(f"{SERVER_URL}/extract", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            analysis = data.get("analysis", {})
            overall_score = analysis.get("overall_score", 0)
            
            print(f"   Overall score: {overall_score}")
            
            if overall_score < 0.3:  # Should be low for non-procedural
                print("✅ Non-procedural text correctly scored low!")
                return True
            else:
                print("❌ Non-procedural text scored too high")
                return False
        else:
            print("Processing failed:", data.get("error"))
            return False
    else:
        print(f"❌ Request failed with status {response.status_code}")
        return False

def main():
    print("Testing Experiment Buddy improvements...\n")
    
    # Test health endpoint first
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy\n")
        else:
            print("❌ Server health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_review_article_detection():
        tests_passed += 1
    
    if test_methods_section():
        tests_passed += 1
        
    if test_non_procedural_scoring():
        tests_passed += 1
    
    print(f"\n📊 Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")

if __name__ == "__main__":
    main()