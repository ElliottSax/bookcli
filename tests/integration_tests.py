#!/usr/bin/env python3
"""
Integration Tests - End-to-End System Validation
Tests complete workflows with realistic data
"""

import sys
import subprocess
import tempfile
from pathlib import Path
import json
import shutil


class IntegrationTestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.root = Path(__file__).parent.parent
        self.test_workspace = None

    def log(self, message, status="INFO"):
        symbols = {"PASS": "✓", "FAIL": "✗", "INFO": "→", "WARN": "⚠"}
        symbol = symbols.get(status, "•")
        print(f"{symbol} {message}")

    def setup_test_workspace(self):
        """Create temporary workspace for testing"""
        self.test_workspace = Path(tempfile.mkdtemp(prefix="booktest_"))
        self.log(f"Test workspace: {self.test_workspace}", "INFO")
        return self.test_workspace

    def cleanup_test_workspace(self):
        """Remove test workspace"""
        if self.test_workspace and self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)
            self.log("Test workspace cleaned up", "INFO")

    def create_sample_source(self):
        """Create realistic sample source material"""
        source_text = """The Shadow Protocol

Chapter One: The Discovery

Dr. Sarah Chen stared at the data streaming across her monitor. Three years of research,
thousands of hours of analysis, and it all pointed to one impossible conclusion: someone
had been manipulating the global financial markets using quantum computing.

Not just manipulating—predicting. With terrifying accuracy.

She leaned back in her chair, the leather creaking in the silent lab. Outside, Boston's
Financial District gleamed in the afternoon sun, oblivious to the bombshell she'd just
uncovered. The algorithm she'd been tracking, the one her supervisor dismissed as a
statistical anomaly, was real. And it was active.

Sarah's phone buzzed. Unknown number.

She hesitated, then answered. "Hello?"

"Dr. Chen." The voice was male, calm, professional. "We need to talk about your research."

Her blood went cold. "Who is this?"

"Someone who knows you've been asking the wrong questions." A pause. "Or perhaps, the
right questions to the wrong people."

The line went dead.

Sarah's hands trembled as she lowered the phone. Her research was theoretical, buried
in academic journals no one read. How could anyone—

The lights went out.

Emergency lighting kicked in, bathing the lab in red. Through the glass wall, she saw
figures moving in the corridor. Three of them. Moving with purpose.

Toward her lab.

Sarah grabbed her laptop, yanked the hard drive from her desktop, and ran for the rear
exit. Behind her, she heard the lab door's electronic lock beep.

They were inside.

She burst through the fire door into the stairwell, taking stairs three at a time.
Eighteen floors to the ground. The hard drive felt like lead in her jacket pocket.

Above her, a door slammed open. Footsteps echoed in the stairwell.

"Dr. Chen!" The same voice from the phone, now amplified. "We just want to talk!"

Sarah kept running. Whatever they wanted, it wasn't a conversation.

She hit the ground floor, crashed through the exit into the parking garage. Her car was
two levels down. She sprinted between concrete pillars, breath burning in her lungs.

A black SUV pulled in front of her, blocking her path.

Sarah pivoted, but two more SUVs sealed off the other exits. She was boxed in.

The rear door of the center vehicle opened. A woman stepped out—mid-forties, expensive
suit, the kind of poise that came from wielding serious power.

"Dr. Chen," she said, voice carrying across the garage. "My name is Director Katherine
Walsh. I'm with a division of the government you've never heard of. And I'm here to
offer you a choice."

Sarah's hand closed around the hard drive in her pocket. "What kind of choice?"

"The kind that determines whether you live through the night."

Walsh pulled out a tablet, tapped it twice, and held it up. The screen showed a map of
Boston. Red dots appeared across the city—dozens of them, converging.

"Those are hostile assets," Walsh said. "They're looking for you. They're looking for
what you found. And they don't take prisoners."

"Who are they?"

"The people who built the algorithm you've been tracking." Walsh's expression hardened.
"They call it the Shadow Protocol. And you just became the only person outside their
organization who can prove it exists."

Sarah looked at the red dots on the screen. They were getting closer.

"You said I had a choice," she said.

Walsh nodded. "Come with me, help us stop them, and maybe—maybe—we all survive this."
She gestured to the SUVs. "Or run, and see how long you last on your own."

Sarah looked at the exits, at the approaching dots on the screen, at Walsh's unwavering
gaze.

She thought about her research, about the pattern she'd uncovered. About the millions of
people who would be affected if the Shadow Protocol continued unchecked.

"If I come with you," Sarah said, "I want full access to your data. I want a team. And I
want answers."

A slight smile crossed Walsh's face. "You'll get two out of three. The third, you'll
have to earn." She opened the SUV door wider. "Time's up, Doctor. Choose."

Sarah took one last look at the world she knew, the normal life she'd built, the safe
academic career that had just evaporated.

Then she climbed into the SUV.

The door closed behind her, and the vehicle accelerated into the night.

Behind them, the first of the red dots entered the parking garage.

[This is a 1000-word sample. A complete source would be 5,000-10,000 words for transformation.]
"""
        return source_text

    def test_orchestrator_initialization(self):
        """Test orchestrator can initialize project"""
        self.log("Testing orchestrator initialization...", "INFO")

        workspace = self.setup_test_workspace()
        source_file = workspace / "test_source.txt"
        source_file.write_text(self.create_sample_source())

        try:
            # Run orchestrator with --no-test flag
            result = subprocess.run(
                ["python3", str(self.root / "scripts/orchestrator.py"),
                 "--source", str(source_file),
                 "--book-name", "test-thriller",
                 "--genre", "thriller",
                 "--target-words", "30000",
                 "--no-test"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.root)
            )

            # Check if workspace was created
            book_workspace = self.root / "workspace" / "test-thriller"

            if book_workspace.exists():
                # Check for expected files
                required_files = [
                    book_workspace / "status.json",
                    book_workspace / "analysis" / "plan.json",
                    book_workspace / "continuity" / "characters.json"
                ]

                all_exist = all(f.exists() for f in required_files)

                if all_exist:
                    self.log("Orchestrator initialized project correctly", "PASS")
                    self.tests_passed += 1

                    # Cleanup
                    shutil.rmtree(book_workspace)
                    return True
                else:
                    missing = [f for f in required_files if not f.exists()]
                    self.log(f"Missing files: {missing}", "FAIL")
                    self.tests_failed += 1
                    return False
            else:
                self.log("Workspace directory not created", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"Orchestrator initialization error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            self.cleanup_test_workspace()

    def test_quality_gate_edge_cases(self):
        """Test quality gate with various edge cases"""
        self.log("Testing quality gate edge cases...", "INFO")

        test_cases = [
            # (input, should_have_forbidden, description)
            ("She delved deeply into the mystery.", True, "forbidden word 'delved'"),
            ("The normal person walked down the street.", False, "normal text"),
            ("He couldn't help but notice her smile.", True, "purple prose phrase"),
            ("Her heart hammered in her chest wildly.", True, "purple prose + adverb"),
            ("The door opened. She entered.", False, "clean prose"),
            ("She felt very scared and quite nervous.", True, "filter words + weak modifiers"),
            ("'Get out,' he said, voice cold.", False, "good dialogue"),
            ("She saw him noticed her watching realized truth.", True, "multiple filter words"),
        ]

        passed = 0
        failed = 0

        for text, should_fail, description in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(text)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ["python3", str(self.root / "scripts/quality_gate.py"),
                     temp_file, "--no-fix"],
                    capture_output=True, text=True, timeout=10
                )

                output = json.loads(result.stdout)
                remaining = output.get('remaining_issues', {})
                has_issues = (
                    len(remaining.get('forbidden_words', [])) > 0 or
                    len(remaining.get('purple_prose', [])) > 0 or
                    len(remaining.get('filter_words', [])) > 0
                )

                if should_fail == has_issues:
                    passed += 1
                else:
                    failed += 1
                    self.log(f"  Failed: {description} (expected issues={should_fail}, got={has_issues})", "WARN")

            except Exception as e:
                self.log(f"  Error testing '{description}': {e}", "WARN")
                failed += 1
            finally:
                Path(temp_file).unlink(missing_ok=True)

        if failed == 0:
            self.log(f"Quality gate edge cases: {passed}/{passed+failed} passed", "PASS")
            self.tests_passed += 1
            return True
        else:
            self.log(f"Quality gate edge cases: {passed}/{passed+failed} passed, {failed} failed", "FAIL")
            self.tests_failed += 1
            return False

    def test_continuity_tracking_workflow(self):
        """Test continuity tracking with realistic workflow"""
        self.log("Testing continuity tracking workflow...", "INFO")

        workspace = self.setup_test_workspace()

        try:
            # Test 1: Add character
            result = subprocess.run(
                ["python3", str(self.root / "scripts/continuity_tracker.py"),
                 str(workspace), "update_character", "Sarah Chen",
                 json.dumps({"chapter": 1, "physical_description": {"age": 32, "occupation": "scientist"}})],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.log("Failed to add character", "FAIL")
                self.tests_failed += 1
                return False

            # Test 2: Add event
            result = subprocess.run(
                ["python3", str(self.root / "scripts/continuity_tracker.py"),
                 str(workspace), "add_event", "1", "Sarah discovers the algorithm"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.log("Failed to add event", "FAIL")
                self.tests_failed += 1
                return False

            # Test 3: Add fact
            result = subprocess.run(
                ["python3", str(self.root / "scripts/continuity_tracker.py"),
                 str(workspace), "add_fact", "1", "The algorithm is called Shadow Protocol"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.log("Failed to add fact", "FAIL")
                self.tests_failed += 1
                return False

            # Test 4: Get summary
            result = subprocess.run(
                ["python3", str(self.root / "scripts/continuity_tracker.py"),
                 str(workspace), "summary"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                summary = json.loads(result.stdout)
                if summary.get('total_characters') == 1 and summary.get('total_events') == 1:
                    self.log("Continuity tracking workflow complete", "PASS")
                    self.tests_passed += 1
                    return True
                else:
                    self.log(f"Unexpected summary: {summary}", "FAIL")
                    self.tests_failed += 1
                    return False
            else:
                self.log("Failed to get summary", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"Continuity tracking error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            self.cleanup_test_workspace()

    def test_kdp_formatter_with_realistic_manuscript(self):
        """Test KDP formatter with multi-chapter manuscript"""
        self.log("Testing KDP formatter with realistic manuscript...", "INFO")

        manuscript = """# The Shadow Protocol

## Chapter 1

Sarah Chen stared at her computer screen. The data was impossible, yet undeniable.

Someone was manipulating the markets using quantum computing.

She reached for her phone, but it rang first. Unknown number.

"Dr. Chen," a voice said. "We need to talk about your research."

* * *

The lights went out.

Sarah grabbed her laptop and ran.

## Chapter 2

Director Walsh sat across from Sarah in the speeding SUV.

"You have two choices," Walsh said. "Help us, or disappear."

Sarah clutched the hard drive. "What is the Shadow Protocol?"

"That's what we need you to figure out."

The vehicle turned down a dark alley. Sarah's normal life was over.

## Chapter 3

The safe house was deep underground, accessible only by elevator.

"Welcome to the Task Force," Walsh said.

Sarah looked around at the banks of computers, the tactical maps. "What am I getting into?"

"The fight of your life."
"""

        workspace = self.setup_test_workspace()
        manuscript_file = workspace / "test_manuscript.md"
        manuscript_file.write_text(manuscript)
        output_dir = workspace / "output"

        try:
            result = subprocess.run(
                ["python3", str(self.root / "scripts/kdp_formatter.py"),
                 str(manuscript_file), str(output_dir)],
                capture_output=True, text=True, timeout=30
            )

            # Check for HTML output (minimum requirement)
            html_file = output_dir / "test_manuscript_kdp.html"

            if html_file.exists():
                html_content = html_file.read_text()

                # Verify HTML structure
                has_title = "Shadow Protocol" in html_content
                has_chapter_1 = "Chapter 1" in html_content
                has_chapter_2 = "Chapter 2" in html_content
                has_scene_break = "scene-break" in html_content or "* * *" in html_content

                if all([has_title, has_chapter_1, has_chapter_2, has_scene_break]):
                    self.log("KDP formatter created valid HTML", "PASS")
                    self.tests_passed += 1
                    return True
                else:
                    self.log("KDP HTML missing expected content", "FAIL")
                    self.tests_failed += 1
                    return False
            else:
                self.log("KDP formatter didn't create HTML file", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"KDP formatter error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            self.cleanup_test_workspace()

    def test_quality_gate_auto_fix(self):
        """Test that auto-fix actually modifies files correctly"""
        self.log("Testing quality gate auto-fix modifications...", "INFO")

        bad_text = """Sarah felt very nervous as she delved into the mystery.
Her heart hammered in her chest. She couldn't help but notice his smoldering gaze.
She realized the truth and felt quite scared."""

        workspace = self.setup_test_workspace()
        test_file = workspace / "bad_chapter.txt"
        test_file.write_text(bad_text)

        try:
            # Run with auto-fix
            result = subprocess.run(
                ["python3", str(self.root / "scripts/quality_gate.py"),
                 str(test_file)],
                capture_output=True, text=True, timeout=10
            )

            output = json.loads(result.stdout)

            # Check that fixes were applied
            if output.get('fixes_applied', 0) > 0:
                # Read modified file
                fixed_text = test_file.read_text()

                # Verify forbidden words removed
                forbidden_present = any(word in fixed_text.lower() for word in
                                      ['delved', 'very', 'quite', 'hammered', 'couldn\'t help'])

                if not forbidden_present:
                    self.log(f"Auto-fix applied {output['fixes_applied']} corrections", "PASS")
                    self.tests_passed += 1
                    return True
                else:
                    self.log("Auto-fix didn't remove all forbidden words", "FAIL")
                    self.tests_failed += 1
                    return False
            else:
                self.log("Auto-fix didn't apply any corrections", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"Auto-fix test error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            self.cleanup_test_workspace()

    def test_full_workflow_simulation(self):
        """Simulate complete book production workflow"""
        self.log("Testing full workflow simulation...", "INFO")

        workspace = self.setup_test_workspace()
        source_file = workspace / "source.txt"
        source_file.write_text(self.create_sample_source())

        try:
            # Step 1: Run orchestrator to create structure
            result = subprocess.run(
                ["python3", str(self.root / "scripts/orchestrator.py"),
                 "--source", str(source_file),
                 "--book-name", "workflow-test",
                 "--genre", "thriller",
                 "--target-words", "30000",
                 "--no-test"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.root)
            )

            book_workspace = self.root / "workspace" / "workflow-test"

            if not book_workspace.exists():
                self.log("Workflow: orchestrator failed to create workspace", "FAIL")
                self.tests_failed += 1
                return False

            # Step 2: Verify analysis files created
            plan_file = book_workspace / "analysis" / "plan.json"
            if not plan_file.exists():
                self.log("Workflow: plan.json not created", "FAIL")
                self.tests_failed += 1
                return False

            plan = json.loads(plan_file.read_text())
            if plan.get('genre') != 'thriller':
                self.log("Workflow: incorrect genre in plan", "FAIL")
                self.tests_failed += 1
                return False

            # Step 3: Verify continuity initialized
            chars_file = book_workspace / "continuity" / "characters.json"
            if not chars_file.exists():
                self.log("Workflow: characters.json not created", "FAIL")
                self.tests_failed += 1
                return False

            # Step 4: Create sample chapter
            chapter_file = book_workspace / "chapters" / "chapter_001.md"
            chapter_file.parent.mkdir(exist_ok=True)
            chapter_file.write_text("""# Chapter 1

Sarah ran through the parking garage. Behind her, footsteps echoed.

"Stop!" a voice shouted.

She didn't stop. The hard drive in her pocket felt heavy. The data it contained
could change everything.

A black SUV blocked her path. Director Walsh stepped out.

"Dr. Chen," Walsh said. "Time to make a choice."

Sarah looked at the exits. All blocked.

"What kind of choice?" Sarah asked.

"The kind that saves your life."
""")

            # Step 5: Run quality gate on chapter
            result = subprocess.run(
                ["python3", str(self.root / "scripts/quality_gate.py"),
                 str(chapter_file)],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.log("Workflow: quality gate failed", "FAIL")
                self.tests_failed += 1
                return False

            # Step 6: Create simple manuscript
            manuscript_file = self.root / "output" / "workflow-test" / "manuscript.md"
            manuscript_file.parent.mkdir(parents=True, exist_ok=True)
            manuscript_file.write_text(f"""# Workflow Test

{chapter_file.read_text()}
""")

            # Step 7: Format for KDP
            result = subprocess.run(
                ["python3", str(self.root / "scripts/kdp_formatter.py"),
                 str(manuscript_file), str(manuscript_file.parent)],
                capture_output=True, text=True, timeout=30
            )

            html_file = manuscript_file.parent / "manuscript_kdp.html"
            if html_file.exists():
                self.log("Full workflow simulation successful", "PASS")
                self.tests_passed += 1

                # Cleanup
                shutil.rmtree(book_workspace)
                shutil.rmtree(manuscript_file.parent)
                return True
            else:
                self.log("Workflow: KDP formatter didn't create output", "FAIL")
                self.tests_failed += 1
                return False

        except Exception as e:
            self.log(f"Workflow simulation error: {e}", "FAIL")
            self.tests_failed += 1
            return False
        finally:
            self.cleanup_test_workspace()

    def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("INTEGRATION TESTS - END-TO-END VALIDATION")
        print("="*60 + "\n")

        # Run tests
        self.test_orchestrator_initialization()
        self.test_quality_gate_edge_cases()
        self.test_quality_gate_auto_fix()
        self.test_continuity_tracking_workflow()
        self.test_kdp_formatter_with_realistic_manuscript()
        self.test_full_workflow_simulation()

        # Report
        print("\n" + "="*60)
        print(f"Integration Tests Passed: {self.tests_passed}")
        print(f"Integration Tests Failed: {self.tests_failed}")
        print("="*60 + "\n")

        if self.tests_failed == 0:
            print("✓ ALL INTEGRATION TESTS PASSED - System validated\n")
            return True
        else:
            print("✗ SOME INTEGRATION TESTS FAILED - Review failures\n")
            return False


def main():
    runner = IntegrationTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
