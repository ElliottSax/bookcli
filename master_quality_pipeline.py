#!/usr/bin/env python3
"""
MASTER QUALITY PIPELINE
=======================
Orchestrates ALL quality improvement processes:
1. Stops Oracle generation
2. Waits for in-progress books
3. Syncs all books from Oracle
4. Runs comprehensive quality review
5. Runs ALL quality fixers in optimal order
6. Generates final report

Quality Fixers (in order):
- AI-ism removal
- Show don't tell conversion
- Dialogue depth enhancement
- Character voice consistency
- Transition smoothing
- Pacing improvement
- Opening/ending fixes
- Short chapter expansion
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm

# Initialize centralized logging and config
setup_logging()
logger = get_logger(__name__)
config = get_config()

# Paths from config
BOOKCLI_DIR = config.paths.base_dir
FICTION_DIR = config.paths.fiction_dir
REPORTS_DIR = config.paths.reports_dir
VENV_PYTHON = "/mnt/e/projects/pod/venv/bin/python3"
SSH_KEY = Path.home() / ".ssh" / "oci_worker_key"
ORACLE_WORKERS = ["147.224.209.15", "64.181.220.95"]

REPORTS_DIR.mkdir(exist_ok=True)

# All quality fixer scripts
QUALITY_SCRIPTS = [
    # Phase 1: Content fixes
    ("show_dont_tell.py", "Show Don't Tell", 60),
    ("dialogue_depth.py", "Dialogue Depth", 60),
    ("character_voice_enhancer.py", "Character Voice", 60),

    # Phase 2: Structure fixes
    ("transition_smoother.py", "Transitions", 60),
    ("pacing_improver.py", "Pacing", 60),

    # Phase 3: Polish
    ("fix_quality_issues.py", "Quality Issues", 120),
]

# Coherency validation (run before fixes to identify critical issues)
COHERENCY_SCRIPT = "coherency_validator.py"


class MasterQualityPipeline:
    """Orchestrates the complete quality improvement pipeline."""

    def __init__(self):
        self.start_time = datetime.now()
        self.stats = {
            "books_reviewed": 0,
            "issues_found": 0,
            "fixes_applied": 0,
            "scripts_run": 0,
            "coherency_issues": 0,
            "books_with_loops": 0,
            "books_with_sync_issues": 0
        }
        self.coherency_results = None

    def stop_oracle_workers(self):
        """Stop Oracle book generation."""
        logger.info("=" * 60)
        logger.info("PHASE 1: STOPPING ORACLE GENERATION")
        logger.info("=" * 60)

        for ip in ORACLE_WORKERS:
            try:
                cmd = f"ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@{ip} 'sudo systemctl stop book-pipeline book-pipeline-2 2>/dev/null; pkill -f autonomous_pipeline || true'"
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                logger.info(f"Stopped generation on {ip}")
            except Exception as e:
                logger.warning(f"Could not stop {ip}: {e}")

    def wait_for_in_progress(self, max_wait_minutes: int = 30):
        """Wait for any in-progress books to complete."""
        logger.info("Waiting for in-progress books to complete...")

        start = time.time()
        while time.time() - start < max_wait_minutes * 60:
            # Check for running pipeline processes
            active = False
            for ip in ORACLE_WORKERS:
                try:
                    cmd = f"ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@{ip} 'pgrep -f \"python.*pipeline\" | wc -l'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=15, text=True)
                    if result.stdout.strip() not in ['0', '']:
                        active = True
                        logger.info(f"Still active processes on {ip}")
                except:
                    pass

            if not active:
                logger.info("All generation complete!")
                return True

            time.sleep(30)

        logger.warning("Timeout waiting - proceeding anyway")
        return False

    def sync_from_oracle(self):
        """Sync all books from Oracle workers."""
        logger.info("=" * 60)
        logger.info("PHASE 2: SYNCING FROM ORACLE")
        logger.info("=" * 60)

        for ip in ORACLE_WORKERS:
            try:
                logger.info(f"Syncing from {ip}...")
                cmd = f"rsync -avz --progress -e 'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no' ubuntu@{ip}:~/output/books/ {FICTION_DIR}/"
                subprocess.run(cmd, shell=True, timeout=600)
                logger.info(f"Synced from {ip}")
            except Exception as e:
                logger.error(f"Sync failed from {ip}: {e}")

        # Count books
        book_count = len([d for d in FICTION_DIR.iterdir() if d.is_dir()])
        logger.info(f"Total books in library: {book_count}")

    def run_coherency_validation(self) -> Dict:
        """
        Run coherency validation to catch:
        - Generation loops (repeated paragraphs/dialogue)
        - Story bible sync issues (content doesn't match outline)
        - Inter-chapter consistency issues (character names, tone drift)
        """
        logger.info("=" * 60)
        logger.info("PHASE 3a: COHERENCY VALIDATION")
        logger.info("=" * 60)

        try:
            # Import the coherency validator
            from coherency_validator import CoherencyValidator

            validator = CoherencyValidator()
            results = validator.validate_all_books(FICTION_DIR, BOOKCLI_DIR / "output/books")

            # Update stats
            self.stats["coherency_issues"] = results.get("critical_issues", 0)
            self.stats["books_with_loops"] = len(results.get("books_with_loops", []))
            self.stats["books_with_sync_issues"] = len(results.get("books_with_sync_issues", []))

            # Log summary
            logger.info(f"Books validated: {results['total_books']}")
            logger.info(f"Passed: {results['passed']}")
            logger.info(f"Failed: {results['failed']}")
            logger.info(f"Critical issues: {results['critical_issues']}")

            if results.get("books_with_loops"):
                logger.warning(f"Books with generation loops: {len(results['books_with_loops'])}")
                for book in results['books_with_loops'][:5]:
                    logger.warning(f"  - {book}")

            if results.get("books_with_sync_issues"):
                logger.warning(f"Books with story bible sync issues: {len(results['books_with_sync_issues'])}")
                for book in results['books_with_sync_issues'][:5]:
                    logger.warning(f"  - {book}")

            if results.get("books_with_consistency_issues"):
                logger.warning(f"Books with consistency issues: {len(results['books_with_consistency_issues'])}")

            # Save summary
            summary_path = REPORTS_DIR / f"coherency_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            summary_path.write_text(json.dumps(results, indent=2))
            logger.info(f"Coherency report saved: {summary_path}")

            self.coherency_results = results
            return results

        except ImportError as e:
            logger.error(f"Could not import coherency_validator: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Coherency validation failed: {e}")
            return {"error": str(e)}

    def run_quality_review(self):
        """Run comprehensive quality review."""
        logger.info("=" * 60)
        logger.info("PHASE 3b: COMPREHENSIVE QUALITY REVIEW")
        logger.info("=" * 60)

        try:
            env = os.environ.copy()
            cmd = [VENV_PYTHON, str(BOOKCLI_DIR / "wrap_up_and_review.py"), "--skip-wrap-up", "--no-ai"]
            result = subprocess.run(cmd, cwd=str(BOOKCLI_DIR), env=env, timeout=7200)

            if result.returncode == 0:
                logger.info("Quality review complete")
                return True
        except Exception as e:
            logger.error(f"Quality review failed: {e}")

        return False

    def run_quality_fixer(self, script_name: str, description: str, timeout_minutes: int) -> Dict:
        """Run a single quality fixer script."""
        script_path = BOOKCLI_DIR / script_name

        if not script_path.exists():
            logger.warning(f"Script not found: {script_name}")
            return {"script": script_name, "status": "not_found"}

        logger.info(f"Running: {description} ({script_name})")

        try:
            env = os.environ.copy()
            start = time.time()
            result = subprocess.run(
                [VENV_PYTHON, str(script_path)],
                cwd=str(BOOKCLI_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_minutes * 60
            )

            elapsed = time.time() - start

            return {
                "script": script_name,
                "description": description,
                "status": "success" if result.returncode == 0 else "error",
                "elapsed_seconds": int(elapsed),
                "output_lines": len(result.stdout.split('\n')) if result.stdout else 0
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"{script_name} timed out after {timeout_minutes} minutes")
            return {"script": script_name, "status": "timeout"}
        except Exception as e:
            logger.error(f"{script_name} failed: {e}")
            return {"script": script_name, "status": "error", "error": str(e)}

    def run_all_fixers(self, parallel: bool = False):
        """Run all quality fixer scripts."""
        logger.info("=" * 60)
        logger.info("PHASE 4: RUNNING ALL QUALITY FIXERS")
        logger.info("=" * 60)

        results = []

        if parallel:
            # Run fixers that don't conflict in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                for script, desc, timeout in QUALITY_SCRIPTS:
                    future = executor.submit(self.run_quality_fixer, script, desc, timeout)
                    futures[future] = script

                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed: {result['script']} - {result['status']}")
        else:
            # Run sequentially
            for script, desc, timeout in QUALITY_SCRIPTS:
                result = self.run_quality_fixer(script, desc, timeout)
                results.append(result)
                self.stats["scripts_run"] += 1
                time.sleep(5)  # Brief pause between scripts

        return results

    def run_ai_deep_fixes(self):
        """Run AI-powered deep fixes on lowest-scoring books."""
        logger.info("=" * 60)
        logger.info("PHASE 5: AI DEEP FIXES FOR PROBLEM BOOKS")
        logger.info("=" * 60)

        # Load latest review
        reports = sorted(REPORTS_DIR.glob("master_report_*.json"))
        if not reports:
            logger.warning("No review reports found - skipping deep fixes")
            return

        try:
            report = json.loads(reports[-1].read_text())
            reviews = report.get("all_reviews", [])

            # Find books with score < 60
            problem_books = [r for r in reviews if r.get("quality_score", 100) < 60]
            logger.info(f"Found {len(problem_books)} books needing deep fixes")

            for book_info in problem_books[:20]:  # Limit to 20
                book_dir = FICTION_DIR / book_info["book"]
                if not book_dir.exists():
                    continue

                logger.info(f"Deep fixing: {book_info['book']} (score: {book_info.get('quality_score', '?')})")

                # Run targeted fixes based on issues
                issues = book_info.get("all_issues", [])

                if any("opening" in i.lower() for i in issues):
                    self._fix_opening_deep(book_dir)

                if any("ending" in i.lower() for i in issues):
                    self._fix_ending_deep(book_dir)

                if any("short" in i.lower() or "word" in i.lower() for i in issues):
                    self._expand_short_chapters(book_dir)

                time.sleep(3)

        except Exception as e:
            logger.error(f"Deep fixes failed: {e}")

    def _fix_opening_deep(self, book_dir: Path):
        """Deep fix for weak opening."""
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            return

        first = chapters[0]
        text = first.read_text()

        prompt = f"""Rewrite the opening of this chapter to create a powerful hook.
Start with action, tension, or intrigue. Draw the reader in immediately.

Current opening:
{text[:2000]}

Return ONLY the improved opening section (first 500-800 words)."""

        try:
            improved = call_llm(prompt, max_tokens=1500, temperature=0.7)
            if improved and len(improved) > 200:
                # Find where to splice
                splice_point = min(2000, len(text) // 3)
                new_text = text.split('\n')[0] + '\n\n' + improved + '\n\n' + text[splice_point:]
                first.write_text(new_text)
                logger.info(f"  Fixed opening in {first.name}")
        except Exception as e:
            logger.warning(f"  Could not fix opening: {e}")

    def _fix_ending_deep(self, book_dir: Path):
        """Deep fix for weak ending."""
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            return

        last = chapters[-1]
        text = last.read_text()

        prompt = f"""Rewrite the ending of this chapter to provide satisfying closure.
Resolve emotional threads and leave readers satisfied.

Current ending:
{text[-2500:]}

Return ONLY the improved ending section (last 600-1000 words)."""

        try:
            improved = call_llm(prompt, max_tokens=1800, temperature=0.7)
            if improved and len(improved) > 200:
                # Replace ending
                splice_point = len(text) - 2500
                new_text = text[:splice_point] + '\n\n' + improved
                last.write_text(new_text)
                logger.info(f"  Fixed ending in {last.name}")
        except Exception as e:
            logger.warning(f"  Could not fix ending: {e}")

    def _expand_short_chapters(self, book_dir: Path):
        """Expand chapters that are too short."""
        min_words = config.quality.min_chapter_words

        for chapter in sorted(book_dir.glob("chapter_*.md")):
            text = chapter.read_text()
            words = len(text.split())

            if words >= min_words:
                continue

            logger.info(f"  Expanding {chapter.name} ({words} words)")

            prompt = f"""Expand this chapter to approximately {config.quality.target_chapter_words} words.
Add sensory details, deeper character thoughts, and natural dialogue.
Keep the same plot.

{text}

Return the COMPLETE expanded chapter."""

            try:
                expanded = call_llm(prompt, max_tokens=5000, temperature=0.7)
                if expanded and len(expanded.split()) > words + 300:
                    chapter.write_text(expanded)
                    logger.info(f"    Expanded to {len(expanded.split())} words")
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"    Could not expand: {e}")

    def generate_final_report(self, fixer_results: List[Dict]):
        """Generate final comprehensive report."""
        logger.info("=" * 60)
        logger.info("PHASE 6: GENERATING FINAL REPORT")
        logger.info("=" * 60)

        # Count books and their status
        books = [d for d in FICTION_DIR.iterdir() if d.is_dir()]
        complete_books = [b for b in books if (b / ".complete").exists() or len(list(b.glob("chapter_*.md"))) >= 10]

        # Calculate total words
        total_words = 0
        for book in books:
            for chapter in book.glob("chapter_*.md"):
                try:
                    total_words += len(chapter.read_text().split())
                except:
                    pass

        report = {
            "generated_at": datetime.now().isoformat(),
            "pipeline_duration_minutes": int((datetime.now() - self.start_time).total_seconds() / 60),
            "library_stats": {
                "total_books": len(books),
                "complete_books": len(complete_books),
                "total_words": total_words,
                "avg_words_per_book": total_words // max(len(books), 1)
            },
            "coherency_validation": {
                "books_with_loops": self.stats.get("books_with_loops", 0),
                "books_with_sync_issues": self.stats.get("books_with_sync_issues", 0),
                "critical_issues": self.stats.get("coherency_issues", 0),
                "loops_fixed": self.coherency_results.get("books_with_loops", []) if self.coherency_results else []
            },
            "fixer_results": fixer_results,
            "successful_fixers": sum(1 for r in fixer_results if r.get("status") == "success"),
        }

        # Save report
        report_path = REPORTS_DIR / f"final_pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2))

        # Print summary
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Duration: {report['pipeline_duration_minutes']} minutes")
        logger.info(f"Total books: {report['library_stats']['total_books']}")
        logger.info(f"Complete books: {report['library_stats']['complete_books']}")
        logger.info(f"Total words: {report['library_stats']['total_words']:,}")
        logger.info(f"Quality scripts run: {report['successful_fixers']}/{len(fixer_results)}")
        logger.info(f"Report saved: {report_path}")
        logger.info("=" * 60)

        return report

    def fix_generation_loops(self):
        """Fix books with detected generation loops by truncating repeated content."""
        logger.info("=" * 60)
        logger.info("PHASE 5a: FIXING GENERATION LOOPS")
        logger.info("=" * 60)

        if not self.coherency_results:
            logger.info("No coherency results - skipping loop fixes")
            return

        books_with_loops = self.coherency_results.get("books_with_loops", [])
        if not books_with_loops:
            logger.info("No books with generation loops detected")
            return

        fixed_count = 0
        for book_name in books_with_loops:
            # Try fiction dir first, then books dir
            book_dir = FICTION_DIR / book_name
            if not book_dir.exists():
                book_dir = BOOKCLI_DIR / "output/books" / book_name
            if not book_dir.exists():
                continue

            # Load coherency report
            report_file = book_dir / "coherency_report.json"
            if not report_file.exists():
                continue

            try:
                report = json.loads(report_file.read_text())
                loop_issues = report.get("loop_issues", [])

                for issue in loop_issues:
                    if issue.get("severity") in ["critical", "major"]:
                        chapter_num = issue.get("chapter")
                        chapter_file = book_dir / f"chapter_{chapter_num:02d}.md"

                        if chapter_file.exists():
                            text = chapter_file.read_text()
                            fixed_text = self._remove_loops_from_text(text, issue)

                            if fixed_text and len(fixed_text) < len(text) * 0.95:
                                # Backup and fix
                                backup = chapter_file.with_suffix('.md.pre-loop-fix')
                                if not backup.exists():
                                    backup.write_text(text)
                                chapter_file.write_text(fixed_text)
                                logger.info(f"Fixed loop in {book_name} chapter {chapter_num}")
                                fixed_count += 1

            except Exception as e:
                logger.warning(f"Could not fix loops in {book_name}: {e}")

        logger.info(f"Fixed {fixed_count} chapters with generation loops")

    def _remove_loops_from_text(self, text: str, issue: Dict) -> str:
        """Remove repeated content from text."""
        import re
        from collections import Counter

        issue_type = issue.get("issue_type", "")

        if issue_type == "paragraph_repeat":
            # Find and deduplicate similar paragraphs
            paragraphs = text.split('\n\n')
            seen = {}
            result = []

            for para in paragraphs:
                normalized = ' '.join(para.lower().split())[:200]
                if normalized not in seen or len(para.strip()) < 50:
                    seen[normalized] = True
                    result.append(para)

            return '\n\n'.join(result)

        elif issue_type == "dialogue_loop":
            # Remove repeated dialogue patterns
            content_preview = issue.get("content_preview", "")
            if content_preview:
                # Extract the repeated phrase
                phrase = content_preview.strip('"').strip("'")[:50]
                if phrase:
                    # Count occurrences
                    pattern = re.escape(phrase)
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    if len(matches) > 3:
                        # Keep first 2 occurrences, remove rest
                        for match in reversed(matches[2:]):
                            # Find sentence boundaries
                            start = text.rfind('.', 0, match.start()) + 1
                            end = text.find('.', match.end()) + 1
                            if end > start:
                                text = text[:start] + text[end:]

            return text

        elif issue_type == "sentence_repeat":
            # Remove repeated sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)
            seen = Counter()
            result = []

            for sent in sentences:
                normalized = ' '.join(sent.lower().split())
                if seen[normalized] < 2:  # Allow max 2 occurrences
                    result.append(sent)
                    seen[normalized] += 1

            return ' '.join(result)

        return text

    def run(self, skip_oracle: bool = False, skip_review: bool = False, skip_coherency: bool = False):
        """Run the complete pipeline."""
        logger.info("=" * 70)
        logger.info("MASTER QUALITY PIPELINE STARTING")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        if not skip_oracle:
            # Phase 1: Stop Oracle
            self.stop_oracle_workers()

            # Phase 2: Wait for completion
            self.wait_for_in_progress(max_wait_minutes=20)

            # Phase 3: Sync
            self.sync_from_oracle()

        # Phase 3a: Coherency Validation (NEW - catches loops, sync issues, consistency)
        if not skip_coherency:
            self.run_coherency_validation()

        if not skip_review:
            # Phase 3b: Traditional Quality Review
            self.run_quality_review()

        # Phase 4: Run all fixers
        fixer_results = self.run_all_fixers(parallel=False)

        # Phase 5a: Fix generation loops (NEW)
        if not skip_coherency:
            self.fix_generation_loops()

        # Phase 5b: Deep fixes for problem books
        self.run_ai_deep_fixes()

        # Phase 6: Final report
        report = self.generate_final_report(fixer_results)

        return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Master Quality Pipeline - Orchestrates all quality improvements")
    parser.add_argument("--skip-oracle", action="store_true", help="Skip stopping/syncing Oracle workers")
    parser.add_argument("--skip-review", action="store_true", help="Skip traditional quality review phase")
    parser.add_argument("--skip-coherency", action="store_true", help="Skip coherency validation (loops, sync, consistency)")
    parser.add_argument("--coherency-only", action="store_true", help="Run only coherency validation")
    args = parser.parse_args()

    pipeline = MasterQualityPipeline()

    if args.coherency_only:
        # Just run coherency validation
        results = pipeline.run_coherency_validation()
        print(f"\nCoherency Validation Complete:")
        print(f"  Books with loops: {len(results.get('books_with_loops', []))}")
        print(f"  Books with sync issues: {len(results.get('books_with_sync_issues', []))}")
        print(f"  Critical issues: {results.get('critical_issues', 0)}")
    else:
        pipeline.run(
            skip_oracle=args.skip_oracle,
            skip_review=args.skip_review,
            skip_coherency=args.skip_coherency
        )
