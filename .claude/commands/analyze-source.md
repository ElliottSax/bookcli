Analyze source material and create transformation plan.

Parameters:
- SOURCE=$1 (path to source file)
- BOOK=$2 (book name for workspace)
- GENRE=$3 (optional, will detect if not provided)

Steps:

1. Read source file completely
2. Analyze structure:
   - Total word count
   - Existing chapter structure (if any)
   - Narrative style (POV, tense)
   - Major plot points
   - Character list
   - Setting details

3. Detect or confirm genre:
   - If GENRE provided, validate appropriateness
   - If not provided, determine from content
   - Load relevant genre module from config/genres/

4. Create workspace:
```bash
mkdir -p workspace/$BOOK/{analysis,chapters,continuity,summaries}
```

5. Generate transformation plan:
   Create workspace/$BOOK/analysis/plan.json with:
   - Source analysis summary
   - Target genre
   - Estimated chapter count (aim for 2500-4500 words per chapter)
   - Overall structure (3-act or genre-appropriate)
   - Transformation approach (modernize, preserve, enhance)

6. Create chapter plan:
   Create workspace/$BOOK/analysis/chapter_plan.json with:
   - Chapter-by-chapter beat outline
   - Target word count per chapter
   - Act structure markers
   - Key scenes to include

7. Initialize character database:
   For each major character found, create entry in:
   workspace/$BOOK/continuity/characters.json

8. Create book config:
   workspace/$BOOK/config.json with:
   - Book name
   - Genre
   - Target word count
   - Source reference
   - Started timestamp

Report summary:
- Genre identified
- Chapters planned
- Main characters catalogued
- Ready for generation

No check-ins needed - make all planning decisions autonomously based on source analysis and genre conventions.
