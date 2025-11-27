Run quality gate on chapter with auto-fix.

Parameters:
- FILE=$1 (chapter file path)

Run quality gate with auto-fix enabled:
```bash
python3 scripts/quality_gate.py $FILE
```

The quality gate will:
1. Check for forbidden words (Tier 1-4)
2. Detect purple prose patterns
3. Find filter words (show don't tell violations)
4. Check weak modifiers
5. Analyze passive voice usage
6. Verify sentence variety
7. Check dialogue ratio
8. Detect repetitive sentence starts

Auto-fix will:
- Replace forbidden words with alternatives
- Remove purple prose phrases
- Remove filter words
- Delete weak modifiers
- Update file automatically

Report results:
- Fixes applied count
- Remaining issues (if any)
- Quality metrics (word count, ratios)
- Pass/fail status

If critical issues remain after auto-fix:
- List specific problems
- Suggest manual corrections
- DO NOT proceed to next chapter until passed

No check-ins - automatically apply fixes and report results.
