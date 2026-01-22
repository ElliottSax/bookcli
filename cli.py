#!/usr/bin/env python3
"""
BookCLI - AI-powered book generation and quality improvement toolkit.

Commands:
    generate    Generate a new book
    fix         Fix quality issues in existing books
    analyze     Analyze book quality
    complete    Complete unfinished books
    worker      Run a background worker

Usage:
    bookcli generate --genre=romance --title="My Book"
    bookcli fix /path/to/book
    bookcli analyze /path/to/book
    bookcli complete --all
    bookcli worker --mode=quality
"""

import argparse
import signal
import sys
from pathlib import Path

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    signal_name = signal.Signals(signum).name
    print(f"\n[{signal_name}] Shutdown requested. Finishing current operation...")
    _shutdown_requested = True


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested

# Ensure lib is importable
sys.path.insert(0, str(Path(__file__).parent))

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config


def cmd_generate(args):
    """Generate a new book."""
    from autonomous_pipeline import ConceptGenerator, BookWriter

    setup_logging()
    logger = get_logger("cli.generate")
    config = get_config()

    generator = ConceptGenerator()
    writer = BookWriter()

    if args.title:
        # Generate with specific title
        concept = {
            'title': args.title,
            'genre': args.genre or 'fiction',
            'subgenre': args.subgenre or '',
            'tone': args.tone or 'engaging',
        }
    else:
        # Auto-generate concept
        concept = generator.generate_concept()
        if not concept:
            logger.error("Failed to generate concept")
            return 1

    logger.info(f"Generating: {concept.get('title')}")

    # Create output directory
    title_slug = concept['title'].replace(' ', '_').replace("'", "")
    book_dir = config.paths.fiction_dir / title_slug
    book_dir.mkdir(parents=True, exist_ok=True)

    # Save concept
    import json
    (book_dir / "metadata.json").write_text(json.dumps(concept, indent=2))

    # Write book
    success = writer.write_book(concept, book_dir)

    if success:
        logger.info(f"Book generated: {book_dir}")
        return 0
    else:
        logger.error("Book generation failed")
        return 1


def cmd_fix(args):
    """Fix quality issues in a book."""
    from fixers import BookContext, TextFixer, QualityFixer
    from lib.backup import BackupManager

    setup_logging()
    logger = get_logger("cli.fix")

    book_path = Path(args.path)
    if not book_path.exists():
        logger.error(f"Book not found: {book_path}")
        return 1

    logger.info(f"Fixing: {book_path.name}")

    # Backup first
    if not args.no_backup:
        backup_mgr = BackupManager(book_path)
        backup_mgr.backup_all_chapters()
        logger.info("Created backups")

    context = BookContext(book_path)
    total_fixes = 0

    # Text fixes
    if args.text or args.all:
        text_fixer = TextFixer(context)
        fixes = text_fixer.fix()
        logger.info(f"Text fixes: {fixes}")
        total_fixes += fixes

    # AI-ism removal
    if args.ai_isms or args.all:
        quality_fixer = QualityFixer(context, fix_ai_isms=True)
        fixes = quality_fixer.fix()
        logger.info(f"AI-ism fixes: {fixes}")
        total_fixes += fixes

    # Expand short chapters
    if args.expand or args.all:
        quality_fixer = QualityFixer(context, expand_short=True)
        fixes = quality_fixer.fix()
        logger.info(f"Expansions: {fixes}")
        total_fixes += fixes

    logger.info(f"Total fixes applied: {total_fixes}")
    return 0


def cmd_analyze(args):
    """Analyze book quality."""
    from comprehensive_scorer import ComprehensiveBookScorer

    setup_logging()
    logger = get_logger("cli.analyze")

    book_path = Path(args.path)
    if not book_path.exists():
        logger.error(f"Book not found: {book_path}")
        return 1

    logger.info(f"Analyzing: {book_path.name}")

    scorer = ComprehensiveBookScorer()
    result = scorer.score_book(book_path)

    print(f"\n{'='*60}")
    print(f"QUALITY ANALYSIS: {book_path.name}")
    print(f"{'='*60}")
    print(f"Overall Score: {result['overall_score']:.1f}/100")
    print(f"\nDimension Scores:")

    for dim, score in sorted(result['dimensions'].items(), key=lambda x: -x[1]):
        bar = '█' * int(score / 10)
        status = '✓' if score >= 70 else '⚠' if score >= 50 else '✗'
        print(f"  {status} {dim:25s}: {bar:10s} {score:.1f}")

    if result.get('issues'):
        print(f"\nIssues Found ({len(result['issues'])}):")
        for issue in result['issues'][:5]:
            print(f"  - {issue}")

    return 0


def cmd_complete(args):
    """Complete unfinished books."""
    from workers import BookCompletionWorker

    setup_logging()
    logger = get_logger("cli.complete")

    worker = BookCompletionWorker()

    if args.all:
        logger.info("Completing all unfinished books...")
        worker.run(max_iterations=1)
    elif args.path:
        # Complete specific book
        book_path = Path(args.path)
        if not book_path.exists():
            logger.error(f"Book not found: {book_path}")
            return 1
        item = {
            'name': book_path.name,
            'path': book_path,
            'chapters': len(list(book_path.glob("chapter_*.md"))),
            'needed': 12 - len(list(book_path.glob("chapter_*.md")))
        }
        worker.process_item(item)
    else:
        logger.error("Specify --all or --path")
        return 1

    return 0


def cmd_worker(args):
    """Run a background worker."""
    from workers import BookCompletionWorker, BookExpansionWorker, BookQualityWorker

    setup_logging()

    workers = {
        'complete': BookCompletionWorker,
        'expand': BookExpansionWorker,
        'quality': BookQualityWorker,
    }

    if args.mode not in workers:
        print(f"Unknown mode: {args.mode}")
        print(f"Available: {', '.join(workers.keys())}")
        return 1

    worker = workers[args.mode]()
    worker.run()
    return 0


def main():
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    parser = argparse.ArgumentParser(
        description='BookCLI - AI-powered book generation toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a new book')
    gen_parser.add_argument('--title', help='Book title')
    gen_parser.add_argument('--genre', help='Book genre')
    gen_parser.add_argument('--subgenre', help='Book subgenre')
    gen_parser.add_argument('--tone', help='Book tone')

    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix quality issues')
    fix_parser.add_argument('path', help='Path to book directory')
    fix_parser.add_argument('--text', action='store_true', help='Apply text fixes')
    fix_parser.add_argument('--ai-isms', action='store_true', help='Remove AI-isms')
    fix_parser.add_argument('--expand', action='store_true', help='Expand short chapters')
    fix_parser.add_argument('--all', action='store_true', help='Apply all fixes')
    fix_parser.add_argument('--no-backup', action='store_true', help='Skip backup')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze book quality')
    analyze_parser.add_argument('path', help='Path to book directory')

    # Complete command
    complete_parser = subparsers.add_parser('complete', help='Complete unfinished books')
    complete_parser.add_argument('--all', action='store_true', help='Complete all')
    complete_parser.add_argument('--path', help='Path to specific book')

    # Worker command
    worker_parser = subparsers.add_parser('worker', help='Run background worker')
    worker_parser.add_argument('--mode', default='complete',
                               choices=['complete', 'expand', 'quality'],
                               help='Worker mode')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'generate': cmd_generate,
        'fix': cmd_fix,
        'analyze': cmd_analyze,
        'complete': cmd_complete,
        'worker': cmd_worker,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
