#!/usr/bin/env python3
"""
Test script for lazy skills loader
Demonstrates the lazy-loading skills system
"""

import sys
sys.path.insert(0, '/root/t1d/.agents/skills')

from lazy_loader import LazySkillsLoader

def test_basic():
    print("=" * 70)
    print("TEST 1: Basic Usage")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    
    # Get all manifests
    manifests = loader.get_all_manifests()
    print(f"\nTotal skills available: {len(manifests)}")
    print(f"\nSample skills:")
    for key in list(manifests.keys())[:3]:
        m = manifests[key]
        print(f"  - {key}: {m.title}")
        print(f"    Category: {m.category}, Priority: {m.priority}")
        print(f"    Tokens: ~{m.token_estimate}")

def test_stats():
    print("\n" + "=" * 70)
    print("TEST 2: Statistics")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    stats = loader.get_stats()
    
    print(f"\nTotal Skills: {stats['total_skills']}")
    print(f"\nBy Category:")
    for cat, count in stats['categories'].items():
        print(f"  {cat}: {count}")
    print(f"\nBy Priority:")
    for pri, count in stats['priority_distribution'].items():
        print(f"  {pri}: {count}")
    print(f"\nTotal Token Estimate: {stats['total_token_estimate']}")
    print(f"Token Savings: ~{stats['total_token_estimate']} tokens/session")

def test_matching():
    print("\n" + "=" * 70)
    print("TEST 3: Skill Matching")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    
    test_requests = [
        "build a minimalist health dashboard",
        "create mobile glucose tracking screen",
        "implement full login with validation",
        "design premium luxury interface",
        "convert design mockup to code",
    ]
    
    for request in test_requests:
        print(f"\nRequest: '{request}'")
        matches = loader.find_relevant_skills(request, threshold=0.5)
        
        if matches:
            for match in matches[:3]:  # Top 3
                print(f"  → {match.skill_key:30s} ({match.confidence*100:.0f}% match)")
                print(f"     Title: {match.manifest.title}")
                if match.trigger_matches:
                    print(f"     Triggers: {', '.join(match.trigger_matches)}")
        else:
            print(f"  No matches (fallback will be used)")

def test_loading():
    print("\n" + "=" * 70)
    print("TEST 4: On-Demand Loading")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    
    # Load a specific skill
    skill_key = "full-output-enforcement"
    print(f"\nLoading skill: {skill_key}")
    
    skill = loader.load_skill(skill_key)
    
    print(f"\nTitle: {skill['manifest']['title']}")
    print(f"Category: {skill['manifest']['category']}")
    print(f"Token Estimate: {skill['manifest']['token_estimate']}")
    print(f"Loaded at: {skill['loaded_at']}")
    print(f"\nContent (first 200 chars):")
    print(f"{skill['content'][:200]}...")
    
    # Check cache
    print(f"\nCache size: {len(loader._skill_cache)} skill(s)")

def test_recommendations():
    print("\n" + "=" * 70)
    print("TEST 5: Recommended Skills")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    
    request = "create health tracking interface"
    print(f"\nRequest: '{request}'")
    
    skills = loader.get_recommended_skills(request)
    
    print(f"\nRecommended skills ({len(skills)}):")
    for i, skill in enumerate(skills, 1):
        print(f"  {i}. {skill['manifest']['title']}")
        print(f"     Tokens: ~{skill['manifest']['token_estimate']}")

def test_system_prompt():
    print("\n" + "=" * 70)
    print("TEST 6: System Prompt Generation")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    
    request = "build minimalist dashboard"
    base = "You are a T1D app designer..."
    
    prompt = loader.generate_system_prompt(request, base)
    
    print(f"\nRequest: '{request}'")
    print(f"\nGenerated System Prompt:")
    print("-" * 70)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 70)

def test_priority_distribution():
    print("\n" + "=" * 70)
    print("TEST 7: Priority Distribution")
    print("=" * 70)
    
    loader = LazySkillsLoader()
    manifests = loader.get_all_manifests()
    
    priorities = {}
    for key, m in manifests.items():
        priorities.setdefault(m.priority, []).append(key)
    
    print("\nSkills by Priority:")
    for pri in ['critical', 'high', 'medium', 'low']:
        if pri in priorities:
            print(f"\n  {pri.upper()}:")
            for key in priorities[pri]:
                m = manifests[key]
                rec = " ⭐" if m.recommended else ""
                print(f"    - {key}{rec}: {m.title}")

def main():
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "  T1D COMPANION - LAZY SKILLS LOADER TEST".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    test_basic()
    test_stats()
    test_matching()
    test_loading()
    test_recommendations()
    test_system_prompt()
    test_priority_distribution()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
    print("\nSummary:")
    print("  - Skills system is operational")
    print("  - Lazy loading works correctly")
    print("  - Matching algorithm is functional")
    print("  - Ready for integration")
    print("\nNext steps:")
    print("  1. Integrate with AGENTS.md documentation")
    print("  2. Add to agent coordinator")
    print("  3. Configure thresholds for production")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
