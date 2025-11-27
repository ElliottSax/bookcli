Assemble complete manuscript and format for KDP.

Parameters:
- BOOK=$1 (book name)

Steps:

1. Verify all chapters complete:
```bash
ls workspace/$BOOK/chapters/chapter_*.md | wc -l
```
Compare with planned chapter count in workspace/$BOOK/analysis/plan.json

2. Combine chapters into manuscript:
   - Read all chapters in order
   - Remove metadata sections
   - Add title page
   - Create table of contents (optional)
   - Combine into single file: output/$BOOK/${BOOK}_manuscript.md

3. Run final quality check on complete manuscript:
```bash
python3 scripts/quality_gate.py output/$BOOK/${BOOK}_manuscript.md
```

4. Generate continuity report:
```bash
python3 scripts/continuity_tracker.py workspace/$BOOK summary > output/$BOOK/continuity_report.json
```

5. Format for KDP:
```bash
python3 scripts/kdp_formatter.py output/$BOOK/${BOOK}_manuscript.md output/$BOOK
```

This creates:
- ${BOOK}_kdp.html (KDP upload format)
- ${BOOK}.epub (if pandoc available)
- ${BOOK}.docx (if pandoc available)
- ${BOOK}_print.pdf (if pandoc + xelatex available)

6. Generate production report:
   Create output/$BOOK/REPORT.md with:
   - Total word count
   - Chapter count
   - Characters tracked
   - Quality metrics summary
   - Files generated
   - Production timeline

7. Report completion:
   - List all generated files
   - Confirm KDP-ready status
   - Provide upload instructions

No check-ins - complete entire assembly process autonomously.
