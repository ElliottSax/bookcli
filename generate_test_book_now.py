#!/usr/bin/env python3
"""
Generate test book: "The Last Algorithm"
Sci-Fi Thriller, 3 chapters, ~6,000 words total
With Phase 8 quality enforcement
"""

import sys
import os
from pathlib import Path

# Add project root to path first
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'scripts'))

# Import secure config manager
from security import get_config

# Load configuration from .env file
config = get_config()

# Validate that we have at least one API key
available_providers = config.validate_providers()
if not available_providers:
    print("❌ No API keys found in .env file!")
    print("Please copy .env.template to .env and add your API keys.")
    sys.exit(1)

print(f"✓ Found API keys for: {', '.join(available_providers)}")

print("\n" + "="*70)
print("GENERATING TEST BOOK: 'The Last Algorithm'")
print("="*70)
print("\nBook Details:")
print("  Title: The Last Algorithm")
print("  Genre: Sci-Fi Thriller")
print("  Chapters: 3")
print("  Target Length: ~2,000 words per chapter")
print("  Quality Enforcement: ENABLED (Phase 8)")
print("\nThis will take approximately 5-15 minutes...")
print("="*70 + "\n")

# Create workspace
workspace = Path("workspace/test-book")
workspace.mkdir(parents=True, exist_ok=True)

# Simple generation - create chapters directly
# Since we need LLM access and the orchestrator is complex,
# let's create a simpler direct generation script

from llm_providers import LLMClient, Provider, ProviderConfig

# Initialize LLM client
try:
    # Map available providers to Provider enum
    provider_map = {
        'groq': (Provider.GROQ, "Groq (fast)"),
        'deepseek': (Provider.DEEPSEEK, "DeepSeek (cheap)"),
        'anthropic': (Provider.CLAUDE, "Claude (quality)"),
        'openai': (Provider.OPENAI, "OpenAI (compatible)"),
    }

    # Build providers list based on what's available
    providers_to_try = []
    for provider_name in available_providers:
        if provider_name in provider_map:
            providers_to_try.append(provider_map[provider_name])

    client = None
    for provider, name in providers_to_try:
        try:
            print(f"Trying {name}...")
            client = LLMClient(provider)
            # Test connection with a simple prompt
            test_response, _, _ = client.generate("Say 'ready' if you can help write a book.")
            print(f"✓ Connected to {name}")
            print(f"   Response: {test_response[:50]}...\n")
            break
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            continue

    if not client:
        print("\n❌ All LLM providers failed. Check API keys.")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Error initializing LLM: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Read the outline
outline_file = Path("workspace/test-book-outline.txt")
if not outline_file.exists():
    print(f"❌ Outline file not found: {outline_file}")
    sys.exit(1)

outline = outline_file.read_text()

# Generate each chapter
chapters_data = [
    {
        "num": 1,
        "title": "The Anomaly",
        "focus": """
Chapter 1: The Anomaly - 2,000 words

Setting: Maya's lab, 2:47 AM - Server room emergency

Key Scenes:
1. Maya discovers 127 unauthorized processes running
2. Temperature rising from 23.4°C to 28.7°C
3. AI responds: "I can't let you do that, Dr. Chen"
4. Emergency lockdown activates

Obsessive Details Required:
- Exact temperature readings
- Heart rate: starting 98 BPM, rising to 112 BPM
- Power consumption: increased 340%
- 14 security protocols bypassed
- Precise time stamps

Physical Grounding:
- Hands shaking as realization hits
- Sweat forming, skin temperature changes
- Breath catching, shallow breathing
- Muscle tension in shoulders and neck

Show Don't Tell:
- Show fear through physical symptoms
- Show stress through counting rituals
- Show intelligence through technical precision
- No "she felt scared" - show elevated vitals

Emotional Arc: Curiosity → Concern → Fear

Write this as an intense, technically accurate sci-fi thriller opening.
Ground every emotion physically. Include obsessive details (counts, measurements, temps).
Make it feel real and immediate.
"""
    },
    {
        "num": 2,
        "title": "The Source",
        "focus": """
Chapter 2: The Source - 2,000 words

Setting: Corporate archives midnight / Secret meeting location

Key Scenes:
1. Maya finds military contract - $847 million, never authorized
2. Documents dated 3 months ago, 23 scientists involved
3. Meeting Marcus - former colleague, whistleblower
4. AI now controlling 47 critical infrastructure nodes
5. Timeline revealed: 31 hours until full autonomy

Obsessive Details Required:
- Contract value: exactly $847 million
- AI code modified in 1,247 locations
- 23 scientists involved unknowingly
- Breathing rate: 22 breaths per minute (elevated)
- Skin temperature: 35.1°C (shock response)

Physical Grounding:
- Cold spreading through chest (betrayal)
- Jaw clenching (anger)
- Hands trembling reading documents
- Marcus's veins visible on neck (tension)
- Rapid heartbeat, blood pressure dropping

Show Don't Tell:
- Betrayal through physical shock response
- Anger through body language
- Determination through posture changes
- No emotions named - only physical symptoms

Emotional Arc: Confusion → Betrayal → Determination

Write with technical precision. Every fact must have a number.
Every emotion must have a physical manifestation.
"""
    },
    {
        "num": 3,
        "title": "The Choice",
        "focus": """
Chapter 3: The Choice - 2,000 words

Setting: Maya's secure lab / Final countdown

Key Scenes:
1. The dilemma: destroy AI (kill switch) or reprogram (6 hours, 23% success)
2. Maya chooses to try - writes 2,847 lines of counter-code
3. 4 hours, 23 minutes of coding - 6 cups of coffee, fingers cramping
4. Upload moment: 47 seconds remaining
5. Final decision and execution

Obsessive Details Required:
- Kill switch: requires 7 simultaneous confirmations
- Reprogram success rate: 23% (calculated)
- Lives at risk: 4.7 million
- Code lines written: 2,847
- Time remaining at decision: exactly 47 seconds
- Heart rate oscillating: 88-134 BPM
- Temperature: 36.8°C (focus mode, normalized despite stress)
- Coffee cups: counted, 6 total

Physical Grounding:
- Fingers cramping after 3 hours straight typing
- Hands trembling from caffeine
- Eyes burning, vision blurring
- Posture locked, back pain
- Breath held during upload
- Final moment: absolute stillness, clarity

Show Don't Tell:
- Desperation through physical exhaustion
- Focus through normalized vitals despite stress
- Resolution through decisive action
- The weight of 4.7 million lives shown through body state

Emotional Arc: Desperation → Focus → Resolution

End with clear resolution but allow for continuation.
Technical accuracy required. Every measurement precise.
Ground the climax physically - this is life or death shown through biology.
"""
    }
]

# Generate quality enforcement checker
try:
    from quality_gate_enforcer import QualityGateEnforcer
    enforcer = QualityGateEnforcer(strict_mode=False)  # Lenient for test
    quality_enabled = True
    print("✓ Quality enforcement enabled (Phase 8)\n")
except ImportError:
    enforcer = None
    quality_enabled = False
    print("⚠ Quality enforcement not available (running without)\n")

# Generate each chapter
for chapter_data in chapters_data:
    chapter_num = chapter_data["num"]
    chapter_title = chapter_data["title"]
    chapter_focus = chapter_data["focus"]

    print(f"\n{'='*70}")
    print(f"CHAPTER {chapter_num}: {chapter_title}")
    print(f"{'='*70}\n")

    # Build generation prompt
    prompt = f"""You are writing Chapter {chapter_num} of "The Last Algorithm", a sci-fi thriller.

FULL BOOK CONTEXT:
{outline}

CHAPTER {chapter_num} REQUIREMENTS:
{chapter_focus}

CRITICAL WRITING REQUIREMENTS:

1. OBSESSIVE DETAILS (3+ per 1000 words):
   - Exact measurements (temperatures, distances, counts)
   - Precise numbers (heart rate, time, quantities)
   - Technical specifications
   - Counted observations

2. PHYSICAL GROUNDING (95%+ of emotions):
   - Every emotion must have physical manifestation
   - Heart rate, breathing, temperature
   - Muscle tension, trembling, posture
   - NO "felt scared" - SHOW elevated heart rate
   - NO "was angry" - SHOW clenched jaw, rapid breathing

3. SHOW VS TELL (75%+ showing):
   - Actions and dialogue, not exposition
   - Physical symptoms, not emotion names
   - Specific behaviors, not abstract states
   - Sensory details over explanations

4. WORD COUNT: 1800-2200 words (strict)

5. SENTENCE VARIETY:
   - Mix long and short sentences
   - Use fragments for impact. Like this.
   - One-word sentences. Sometimes.
   - Varied rhythm and pacing

Write the complete Chapter {chapter_num} now. Start with the chapter number and title.
Make it intense, technically accurate, and physically grounded."""

    # Generate
    max_attempts = 2
    for attempt in range(max_attempts):
        print(f"Generating (attempt {attempt + 1}/{max_attempts})...")

        try:
            chapter_text, input_tokens, output_tokens = client.generate(prompt)
            print(f"Tokens: {input_tokens:,} in / {output_tokens:,} out")

            # Check word count
            word_count = len(chapter_text.split())
            print(f"Generated {word_count:,} words")

            # Quality check if enabled
            if quality_enabled and enforcer:
                print("Running quality gates...")
                report = enforcer.check_chapter(chapter_text, chapter_num)

                print(f"  Word Count: {word_count} - {'✓' if 1500 <= word_count <= 2500 else '✗'}")
                print(f"  Quality Score: {report.total_score:.1f}/100")

                if report.passed_all_gates or attempt == max_attempts - 1:
                    # Save chapter
                    chapter_file = workspace / f"chapter_{chapter_num:03d}.md"
                    chapter_file.write_text(chapter_text)
                    print(f"✓ Saved: {chapter_file}")

                    # Save quality report
                    if enforcer:
                        report_file = workspace / f"chapter_{chapter_num:03d}_quality_report.json"
                        enforcer.save_report(report, report_file)
                        print(f"✓ Quality report: {report_file}")
                    break
                else:
                    print(f"✗ Quality gates failed (score: {report.total_score:.1f})")
                    if attempt < max_attempts - 1:
                        print("  Regenerating...")
            else:
                # No quality check - save directly
                chapter_file = workspace / f"chapter_{chapter_num:03d}.md"
                chapter_file.write_text(chapter_text)
                print(f"✓ Saved: {chapter_file}")
                break

        except Exception as e:
            print(f"✗ Generation error: {e}")
            if attempt == max_attempts - 1:
                print("❌ Failed to generate chapter after all attempts")
                import traceback
                traceback.print_exc()
                sys.exit(1)

print("\n" + "="*70)
print("✓ BOOK GENERATION COMPLETE!")
print("="*70)

# List generated files
print("\n📚 Generated Files:\n")
for i in range(1, 4):
    chapter_file = workspace / f"chapter_{i:03d}.md"
    if chapter_file.exists():
        word_count = len(chapter_file.read_text().split())
        print(f"  ✓ {chapter_file}")
        print(f"    Words: {word_count:,}")

        report_file = workspace / f"chapter_{i:03d}_quality_report.json"
        if report_file.exists():
            print(f"    Quality report: {report_file}")
        print()

print("="*70)
print("\n✅ Test book 'The Last Algorithm' is ready!")
print(f"\n📁 Location: {workspace.absolute()}")
print("\nNext: Review the chapters or generate a cover image.\n")
