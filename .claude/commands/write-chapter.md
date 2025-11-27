Generate complete chapter following all quality rules.

Load context and rules:
- Read .claude/core-rules.md
- Read .claude/forbidden-lists.md
- Read config/genres/$GENRE.md (from workspace config)
- Read config/craft/scene-structure.md
- Load continuity from workspace/$BOOK/continuity/

Extract parameters:
- BOOK=$1 (book name)
- CHAPTER=$2 (chapter number)
- GENRE from workspace/$BOOK/config.json

Get context:
```bash
python3 scripts/continuity_tracker.py workspace/$BOOK get_context $CHAPTER
```

Read chapter plan:
```bash
cat workspace/$BOOK/analysis/chapter_plan.json
```

Generate the complete chapter:

1. **Apply ALL loaded rules** - mandatory compliance
2. **Use continuity context** - maintain consistency
3. **Follow genre conventions** - from loaded genre module
4. **Target word count** - from chapter plan
5. **End on hook** - cliffhanger or revelation
6. **NO CHECK-INS** - make all creative decisions autonomously

Write complete chapter to: workspace/$BOOK/chapters/chapter_$CHAPTER.md

After writing chapter:

1. Run quality gate with auto-fix:
```bash
python3 scripts/quality_gate.py workspace/$BOOK/chapters/chapter_$CHAPTER.md
```

2. Extract and update continuity:
Parse chapter for:
- New characters introduced
- Major events occurred
- Facts established
- Plot threads advanced/resolved
- Character knowledge gained

Update continuity:
```bash
# For each new character
python3 scripts/continuity_tracker.py workspace/$BOOK update_character "Name" '{"chapter": '$CHAPTER', ...}'

# For each event
python3 scripts/continuity_tracker.py workspace/$BOOK add_event $CHAPTER "Event description"

# For each fact
python3 scripts/continuity_tracker.py workspace/$BOOK add_fact $CHAPTER "Fact description"
```

3. Generate chapter summary for next chapter context:
Create workspace/$BOOK/summaries/chapter_$CHAPTER.md with:
- Key events (3-5 bullets)
- Character states at end
- Active plot threads
- Cliffhanger/hook for next chapter

4. Report completion:
- Word count
- Quality gate results
- Continuity items tracked

IMPORTANT: Write the COMPLETE chapter text, not an outline or summary. The chapter should be publication-ready prose.
