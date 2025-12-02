#!/usr/bin/env python3
"""
Test script: Regenerate Chapter 13 with ultra-tier prompts

Goal: Demonstrate improved first-pass quality
- Original: 1,590 words, ~7.3/10 quality
- Target: 3,500 words, 8.0+/10 quality
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from prompt_builder import PromptBuilder

def main():
    print("="*70)
    print("CHAPTER 13 REGENERATION TEST - ULTRA-TIER PROMPTS")
    print("="*70)
    print()

    # Initialize prompt builder (will load ultra-tier config)
    builder = PromptBuilder(config_dir="config")

    # Chapter 13 outline (from existing chapter)
    outline = """
    Chapter 13: The Morning After (First morning without armor)

    Key scenes:
    1. Catherine wakes to real sunlight for first time in 7 years (no helmet)
    2. Comes downstairs, watches Elara work (counting habit emerging)
    3. Breakfast: Catherine relearning to eat for pleasure (porridge/honey)
    4. Elara examines Catherine's feet (silver scars, deformed bones)
    5. REVELATION: Threads still embedded in bones (must surgically extract)
    6. Elara explains: 2 months to live if not extracted, 1-2 weeks surgery
    7. High risk: permanent nerve damage, may never walk properly
    8. Catherine's fear: being "ordinary" without armor/magic
    9. CLIMAX: Catherine says "I love you" (first full confession)
    10. Elara can't say it back yet (afraid of losing Catherine)
    11. Schedule extraction for tomorrow, both anxious about what comes next

    Emotional arc: Hope → domestic intimacy → devastating revelation →
                   vulnerability → love confession → bittersweet acceptance

    Target word count: 3,500 words
    Obsession focus: Counting (steps, heartbeats, tools), temperature, hands
    """

    # Continuity context
    context = """
    Previous chapters summary:
    - Day 1: Catherine arrived in armor, Elara hears armor screaming
    - Days 1-38: Slow armor removal (piece by piece)
    - Day 38: Final sabatons removed, ALL armor plates gone
    - Catherine learning to walk on bare feet (uneven, painful, 30 steps so far)
    - Both sleeping together (no physical intimacy yet beyond kissing)
    - Catherine's body healing: temp 35.8°C (from 32°C), heart 72 BPM (from 62)
    - Both kingdoms hunting Catherine (deserter + spy)
    - Council pressure on Elara (war started, forge at risk)
    - Catherine said "I love you" end of Ch12, Elara didn't respond yet

    Character states:
    - Catherine: Free of armor, frightened of being ordinary, grateful, in love
    - Elara: Exhausted from 38 days of surgery, counting obsessively,
             afraid of loss (mother died, doesn't want to fail again)

    Obsessive details to continue:
    - Elara counts everything (heartbeats, steps, tools, ceiling beams)
    - Catherine has 3 freckles on right hand (Ursa Minor pattern)
    - Elara has 18 burn scars on hands
    - Temperature tracking: Catherine healing = warming
    - Heartbeat tracking: Catherine healing = faster BPM
    """

    # Source material themes
    source = """
    Themes to continue:
    - Prison of perfection: Catherine freed from armor, now afraid of being imperfect
    - Truth of touch: Elara reads metal, Catherine forbidden touch for 7 years
    - Choosing softness: Both trained to be hard (metal/armor), learning to be soft
    - Counting as control: Elara counts when anxious, Catherine learning same habit
    - Fire symbolism: Destructive (Elara's mother) + creative (forge, love)

    Genre: Sapphic fantasy romance (slow burn)
    """

    # Build enhanced prompt with ultra-tier requirements
    print("Building ultra-tier prompt...")
    print()

    prompt = builder.build_chapter_prompt(
        chapter_num=13,
        outline=outline,
        context=context,
        source_excerpt=source,
        variation_focus=None,  # Use balanced/default
        num_examples=2,
        target_words=3500,
        genre="romance"  # Use romance-specific requirements
    )

    # Display the generated prompt (first 3000 chars)
    print("GENERATED PROMPT (excerpt):")
    print("-"*70)
    print(prompt[:3000])
    print()
    print(f"[...{len(prompt) - 3000} more characters...]")
    print()
    print("-"*70)
    print()

    print(f"Total prompt length: {len(prompt)} characters")
    print(f"Total prompt tokens (estimate): {len(prompt.split())}")
    print()

    # Save full prompt to file for inspection
    output_path = Path("test_chapter13_prompt.txt")
    with open(output_path, 'w') as f:
        f.write(prompt)

    print(f"✓ Full prompt saved to: {output_path}")
    print()

    print("="*70)
    print("NEXT STEPS:")
    print("="*70)
    print()
    print("1. Review the generated prompt in test_chapter13_prompt.txt")
    print("2. Verify it includes:")
    print("   - Ultra-tier quality requirements (8.0+ target)")
    print("   - Word count enforcement (3,500 words ±15%)")
    print("   - Romance-specific requirements (touch cataloging, etc.)")
    print("   - Ultra-tier examples (depth_focused, emotion_focused)")
    print("   - Quality checkpoints")
    print()
    print("3. To generate the chapter, use orchestrator.py with --use-api:")
    print()
    print("   python3 scripts/orchestrator.py \\")
    print("     --source workspace/threads-of-fire/outline.txt \\")
    print("     --book-name threads-of-fire \\")
    print("     --genre romance \\")
    print("     --chapter 13 \\")
    print("     --use-api --provider groq \\")
    print("     --target-words 3500")
    print()
    print("4. Compare results:")
    print(f"   - Original: 1,590 words")
    print(f"   - Target: 3,500 words (±15% = 2,975-4,025 words)")
    print(f"   - Original quality: ~7.3/10")
    print(f"   - Target quality: 8.0+/10")
    print()

if __name__ == "__main__":
    main()
