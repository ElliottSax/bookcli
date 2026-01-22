# Metadata Generation Setup - Complete

## Overview

I've created a comprehensive system to generate `metadata.json` files for 10 fiction books using the Groq API with the llama-3.3-70b-versatile model.

## Files Created

### 1. Main Script: `generate_all_metadata.py`
**Location:** `/mnt/e/projects/bookcli/generate_all_metadata.py`

A robust Python script that:
- Auto-installs the `requests` library if missing
- Processes 10 target books in sequence
- Reads outline.json and chapter_01.md for context
- Counts total words across all available chapters
- Calls Groq API to generate professional metadata
- Saves metadata.json with all required fields
- Handles errors gracefully
- Includes rate limiting (2-second delays between API calls)
- Provides detailed progress output

### 2. Instructions: `RUN_METADATA_GENERATION.md`
**Location:** `/mnt/e/projects/bookcli/RUN_METADATA_GENERATION.md`

Complete documentation including:
- Quick start command
- Detailed process explanation
- Expected output examples
- Verification commands
- Troubleshooting guide
- API configuration details

### 3. Example Output: `EXAMPLE_METADATA.json`
**Location:** `/mnt/e/projects/bookcli/EXAMPLE_METADATA.json`

Sample metadata showing the expected format and quality of generated data.

## Target Books (10 total)

All books are in `/mnt/e/projects/bookcli/output/fiction/`:

1. **A_Room_of_Her_Own_The_Founders_Manifesto** - Women in tech startup story
2. **A_View_from_Abroad_A_Semester_to_Remember** - Study abroad narrative
3. **Alice_in_the_Metaverse** - VR/Metaverse reimagining
4. **All_Quiet_on_the_Digital_Front** - Digital warfare story
5. **Anti-Nephi-Lehis_The_Pacifists** - Book of Mormon reimagining
6. **Brother_of_Jared_Submarine_Startup** - Startup/faith narrative
7. **Descent_A_Deep_Sea_Thriller** - Deep sea thriller
8. **Dracula_Inc_Blood_Money** - Corporate vampire story
9. **Gadianton_Organized_Crime** - Crime thriller
10. **Ghosts_of_Gentrification** - Urban gentrification story

All books have been verified to have:
- ✅ `outline.json` file
- ✅ `chapter_01.md` file
- ✅ Multiple additional chapters
- ❌ NO existing `metadata.json` (ready for generation)

## How to Run

### Simple One-Line Command:
```bash
cd /mnt/e/projects/bookcli && python3 generate_all_metadata.py
```

### Alternative (if in project directory):
```bash
python3 generate_all_metadata.py
```

## What Gets Generated

Each `metadata.json` file contains:

```json
{
  "title": "Book Title",
  "subtitle": "Compelling subtitle",
  "author": "Author name",
  "description_short": "1-2 sentence hook (max 150 chars)",
  "description_long": "2-3 paragraph detailed description (400-600 chars)",
  "keywords": ["keyword1", "keyword2", ... 7 total],
  "categories": ["Category1", "Category2", "Category3"],
  "age_rating": "Adult",
  "page_count": 180,
  "word_count": 45231,
  "comparable_titles": [
    "Title 1 by Author 1",
    "Title 2 by Author 2",
    "Title 3 by Author 3"
  ]
}
```

## API Configuration

- **Provider:** Groq
- **Model:** llama-3.3-70b-versatile
- **API Key:** Set via GROQ_API_KEY environment variable
- **Endpoint:** https://api.groq.com/openai/v1/chat/completions
- **Timeout:** 90 seconds per request
- **Rate Limiting:** 2-second delay between successful API calls

## Verification After Running

Check all metadata files were created:
```bash
ls -la /mnt/e/projects/bookcli/output/fiction/*/metadata.json
```

Count how many were created:
```bash
ls /mnt/e/projects/bookcli/output/fiction/*/metadata.json | wc -l
```

View a specific file:
```bash
cat /mnt/e/projects/bookcli/output/fiction/Alice_in_the_Metaverse/metadata.json
```

Pretty-print JSON:
```bash
python3 -m json.tool /mnt/e/projects/bookcli/output/fiction/Alice_in_the_Metaverse/metadata.json
```

## Expected Runtime

- **Per book:** ~5-10 seconds (API call + processing)
- **Total time:** ~1-2 minutes for all 10 books (with rate limiting)

## Error Handling

The script handles:
- Missing dependencies (auto-installs requests)
- Missing files (skips with error message)
- Existing metadata (skips to avoid overwriting)
- API timeouts (90-second timeout per request)
- JSON parsing errors (detailed error messages)
- Network failures (graceful error handling)

## Success Criteria

✅ Script completes without errors
✅ 10 new metadata.json files created
✅ Each file contains all required fields
✅ Word counts and page counts are accurate
✅ Descriptions are compelling and professional
✅ Keywords and categories are relevant
✅ Comparable titles are real published books

## Next Steps After Generation

Once metadata files are generated, you can:

1. **Review the metadata** for quality and accuracy
2. **Edit any files** that need adjustments
3. **Use the metadata** for publishing to platforms like Amazon KDP
4. **Generate more books** by adding titles to the BOOKS list
5. **Integrate metadata** into your book publishing pipeline

## Troubleshooting

### Script fails with "No module named 'requests'"
The script should auto-install. If not:
```bash
pip3 install requests
```

### API errors
- Check internet connection
- Verify API key is valid
- Check Groq API status at status.groq.com

### JSON parsing errors
- The script will show the problematic response
- Usually means API returned non-JSON content
- Try running the script again (may be temporary API issue)

### Book not found
- Verify book name matches directory name exactly
- Check that outline.json and chapter_01.md exist
- Directory path: `/mnt/e/projects/bookcli/output/fiction/BOOK_NAME/`

## Files Overview

```
/mnt/e/projects/bookcli/
├── generate_all_metadata.py          # Main script (READY TO RUN)
├── RUN_METADATA_GENERATION.md        # Detailed instructions
├── EXAMPLE_METADATA.json             # Sample output
├── METADATA_GENERATION_SUMMARY.md    # This file
└── output/fiction/
    ├── A_Room_of_Her_Own_The_Founders_Manifesto/
    │   ├── outline.json              ✅ Exists
    │   ├── chapter_01.md             ✅ Exists
    │   └── metadata.json             ⚡ Will be generated
    ├── A_View_from_Abroad_A_Semester_to_Remember/
    │   └── ... (same structure)
    └── ... (8 more books)
```

## Contact & Support

For issues or questions:
1. Check RUN_METADATA_GENERATION.md for detailed instructions
2. Review EXAMPLE_METADATA.json for expected format
3. Check script output for specific error messages
4. Verify all prerequisites are installed

---

**Status:** ✅ READY TO RUN
**Created:** 2025-12-31
**Script:** generate_all_metadata.py
**Books:** 10 fiction titles ready for metadata generation
