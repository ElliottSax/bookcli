#!/usr/bin/env python3
"""
Self-Test Framework for Book Production System
Validates all components before production run
"""

import sys
import subprocess
from pathlib import Path
import json
import tempfile


class TestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.root = Path(__file__).parent.parent

    def log(self, message, status="INFO"):
        symbols = {"PASS": "✓", "FAIL": "✗", "INFO": "→"}
        symbol = symbols.get(status, "•")
        print(f"{symbol} {message}")

    def test_quality_gate(self):
        """Test quality gate with known bad text"""
        self.log("Testing quality gate auto-fix...", "INFO")

        bad_text = """She felt very nervous as she delved into the mystery.
His heart hammered in his chest. The electricity between them was palpable.
She couldn't help but notice his smoldering gaze."""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(bad_text)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python3", str(self.root / "scripts/quality_gate.py"), temp_file],
                capture_output=True, text=True, timeout=10
            )

            output = json.loads(result.stdout)

            # Check that fixes were applied
            if output.get('fixes_applied', 0) > 0:
                self.log(f"Quality gate fixed {output['fixes_applied']} issues", "PASS")
                self.tests_passed += 1
                return True
            else:
                self.log("Quality gate didn't apply fixes", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"Quality gate test error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_continuity_tracker(self):
        """Test continuity tracking system"""
        self.log("Testing continuity tracker...", "INFO")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Test initialization
                result = subprocess.run(
                    ["python3", str(self.root / "scripts/continuity_tracker.py"),
                     tmpdir, "summary"],
                    capture_output=True, text=True, timeout=10
                )

                if result.returncode == 0:
                    summary = json.loads(result.stdout)
                    if "total_characters" in summary:
                        self.log("Continuity tracker initialized", "PASS")
                        self.tests_passed += 1
                        return True

                self.log("Continuity tracker test failed", "FAIL")
                self.tests_failed += 1
                return False

            except Exception as e:
                self.log(f"Continuity tracker error: {e}", "FAIL")
                self.tests_failed += 1
                return False

    def test_forbidden_word_detection(self):
        """Test that forbidden words are detected"""
        self.log("Testing forbidden word detection...", "INFO")

        test_cases = [
            ("delve", True),
            ("leverage", True),
            ("embark", True),
            ("normal", False),
            ("write", False)
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            for word, should_detect in test_cases:
                Path(temp_file).write_text(f"The character decided to {word} into the problem.")

                result = subprocess.run(
                    ["python3", str(self.root / "scripts/quality_gate.py"),
                     temp_file, "--no-fix"],
                    capture_output=True, text=True, timeout=10
                )

                try:
                    output = json.loads(result.stdout)
                    # Check only critical issues (forbidden words, purple prose)
                    remaining = output.get('remaining_issues', {})
                    has_critical_issues = (
                        len(remaining.get('forbidden_words', [])) > 0 or
                        len(remaining.get('purple_prose', []))  > 0
                    )

                    if should_detect and has_critical_issues:
                        continue  # Correct detection
                    elif not should_detect and not has_critical_issues:
                        continue  # Correct non-detection
                    else:
                        self.log(f"Word '{word}' detection incorrect (expected detect={should_detect}, got critical issues={has_critical_issues})", "FAIL")
                        self.tests_failed += 1
                        return False
                except json.JSONDecodeError:
                    self.log(f"Quality gate returned invalid JSON for word '{word}'", "FAIL")
                    self.tests_failed += 1
                    return False

            self.log("Forbidden word detection working", "PASS")
            self.tests_passed += 1
            return True

        except Exception as e:
            self.log(f"Detection test error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_config_files_exist(self):
        """Verify all required config files exist"""
        self.log("Checking configuration files...", "INFO")

        required_files = [
            ".claude/core-rules.md",
            ".claude/forbidden-lists.md",
            "config/genres/thriller.md",
            "config/genres/romance.md",
            "config/genres/fantasy.md",
            "config/craft/scene-structure.md"
        ]

        missing = []
        for file_path in required_files:
            if not (self.root / file_path).exists():
                missing.append(file_path)

        if missing:
            self.log(f"Missing config files: {', '.join(missing)}", "FAIL")
            self.tests_failed += 1
            return False

        self.log(f"All {len(required_files)} config files present", "PASS")
        self.tests_passed += 1
        return True

    def test_scripts_executable(self):
        """Verify all scripts can be executed"""
        self.log("Checking scripts...", "INFO")

        scripts = [
            "scripts/quality_gate.py",
            "scripts/continuity_tracker.py",
            "scripts/kdp_formatter.py",
            "scripts/orchestrator.py"
        ]

        for script_path in scripts:
            script = self.root / script_path
            if not script.exists():
                self.log(f"Missing script: {script_path}", "FAIL")
                self.tests_failed += 1
                return False

            # Make executable
            script.chmod(0o755)

        self.log(f"All {len(scripts)} scripts present", "PASS")
        self.tests_passed += 1
        return True

    def test_kdp_formatter(self):
        """Test KDP formatter with sample manuscript"""
        self.log("Testing KDP formatter...", "INFO")

        sample_manuscript = """# Test Book

## Chapter 1

This is the first chapter of the test book.

It has multiple paragraphs.

## Chapter 2

This is the second chapter.

* * *

With a scene break.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            manuscript_file = Path(tmpdir) / "test_manuscript.md"
            manuscript_file.write_text(sample_manuscript)
            output_dir = Path(tmpdir) / "output"

            try:
                result = subprocess.run(
                    ["python3", str(self.root / "scripts/kdp_formatter.py"),
                     str(manuscript_file), str(output_dir)],
                    capture_output=True, text=True, timeout=30
                )

                # Check that HTML was created (minimum requirement)
                html_file = output_dir / "test_manuscript_kdp.html"
                if html_file.exists() and result.returncode == 0:
                    self.log("KDP formatter created HTML", "PASS")
                    self.tests_passed += 1
                    return True
                else:
                    self.log("KDP formatter failed", "FAIL")
                    self.tests_failed += 1
                    return False

            except Exception as e:
                self.log(f"KDP formatter error: {e}", "FAIL")
                self.tests_failed += 1
                return False

    def run_all_tests(self):
        """Run all tests and report results"""
        print("\n" + "="*60)
        print("BOOK PRODUCTION SYSTEM - SELF TEST")
        print("="*60 + "\n")

        # Run tests
        self.test_config_files_exist()
        self.test_scripts_executable()
        self.test_quality_gate()
        self.test_continuity_tracker()
        self.test_forbidden_word_detection()
        self.test_kdp_formatter()

        # Report
        print("\n" + "="*60)
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_failed}")
        print("="*60 + "\n")

        if self.tests_failed == 0:
            print("✓ ALL TESTS PASSED - System ready for production\n")
            return True
        else:
            print("✗ SOME TESTS FAILED - Fix issues before production\n")
            return False


def main():
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
