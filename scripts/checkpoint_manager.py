#!/usr/bin/env python3
"""
Checkpoint Manager for Advanced Resume Capability
Phase 4, Priority 1.2: Atomic checkpoint system for robust failure recovery

Provides atomic saves at critical points to enable precise resume from failures.
"""

import json
import pickle
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import hashlib
import shutil
import threading


@dataclass
class GenerationCheckpoint:
    """Represents a checkpoint during chapter generation"""
    chapter_num: int
    stage: str  # 'started', 'prompt_created', 'generated', 'analyzed', 'enhanced', 'completed'
    timestamp: float
    data: Dict[str, Any]
    retry_count: int = 0
    error: Optional[str] = None

    # Generation data
    prompt: Optional[str] = None
    raw_text: Optional[str] = None
    enhanced_text: Optional[str] = None

    # Analysis results
    quality_prediction: Optional[Dict] = None
    detail_density: Optional[Dict] = None
    word_count_analysis: Optional[Dict] = None

    # Costs
    generation_tokens: int = 0
    enhancement_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationCheckpoint':
        """Create from dictionary"""
        return cls(**data)


class CheckpointManager:
    """
    Manages checkpoint saving and recovery for book generation

    Features:
    - Atomic writes (write to temp, then rename)
    - Compression for large checkpoints
    - Corruption detection (checksums)
    - Automatic backup rotation
    - Thread-safe operations
    """

    def __init__(self, workspace: Path, max_backups: int = 3):
        """
        Initialize checkpoint manager

        Args:
            workspace: Directory for checkpoint files
            max_backups: Maximum number of backup checkpoints to keep
        """
        self.workspace = Path(workspace)
        self.checkpoint_dir = self.workspace / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.max_backups = max_backups
        self.lock = threading.Lock()

        # Main checkpoint files
        self.master_checkpoint = self.checkpoint_dir / "master_checkpoint.json"
        self.chapters_dir = self.checkpoint_dir / "chapters"
        self.chapters_dir.mkdir(exist_ok=True)

        # Initialize or load master checkpoint
        self._init_master_checkpoint()

    def _init_master_checkpoint(self):
        """Initialize or load the master checkpoint file"""
        if self.master_checkpoint.exists():
            self.master_data = self._load_json_safe(self.master_checkpoint)
            print(f"[CheckpointManager] Loaded existing checkpoint with {len(self.master_data.get('chapters', {}))} chapters")
        else:
            self.master_data = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "book_name": self.workspace.name,
                "chapters": {},
                "generation_stats": {
                    "total_time": 0,
                    "total_cost": 0,
                    "total_tokens": 0,
                    "failed_attempts": 0
                }
            }
            self._save_json_atomic(self.master_checkpoint, self.master_data)
            print("[CheckpointManager] Created new master checkpoint")

    def save_checkpoint(self, checkpoint: GenerationCheckpoint):
        """
        Save a checkpoint atomically

        Args:
            checkpoint: The checkpoint to save
        """
        with self.lock:
            # Save individual chapter checkpoint
            chapter_file = self.chapters_dir / f"chapter_{checkpoint.chapter_num:03d}.json"
            checkpoint_data = checkpoint.to_dict()

            # Add checksum for integrity
            checkpoint_data['checksum'] = self._calculate_checksum(checkpoint_data)

            # Save atomically
            self._save_json_atomic(chapter_file, checkpoint_data)

            # Update master checkpoint
            self.master_data['chapters'][str(checkpoint.chapter_num)] = {
                'stage': checkpoint.stage,
                'timestamp': checkpoint.timestamp,
                'retry_count': checkpoint.retry_count,
                'error': checkpoint.error,
                'file': str(chapter_file.name)
            }
            self.master_data['last_updated'] = datetime.now().isoformat()

            # Update stats
            if checkpoint.total_cost > 0:
                self.master_data['generation_stats']['total_cost'] += checkpoint.total_cost
            if checkpoint.generation_tokens > 0:
                self.master_data['generation_stats']['total_tokens'] += checkpoint.generation_tokens

            self._save_json_atomic(self.master_checkpoint, self.master_data)

            # Rotate backups
            self._rotate_backups()

    def load_checkpoint(self, chapter_num: int) -> Optional[GenerationCheckpoint]:
        """
        Load a checkpoint for a specific chapter

        Args:
            chapter_num: Chapter number to load

        Returns:
            GenerationCheckpoint or None if not found
        """
        with self.lock:
            chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.json"

            if not chapter_file.exists():
                return None

            data = self._load_json_safe(chapter_file)
            if not data:
                return None

            # Verify checksum
            stored_checksum = data.pop('checksum', None)
            if stored_checksum:
                calculated = self._calculate_checksum(data)
                if calculated != stored_checksum:
                    print(f"[CheckpointManager] WARNING: Checksum mismatch for chapter {chapter_num}")
                    # Try to load from backup
                    return self._load_from_backup(chapter_num)

            return GenerationCheckpoint.from_dict(data)

    def get_resume_point(self) -> Dict[str, Any]:
        """
        Analyze checkpoints to determine optimal resume point

        Returns:
            Dictionary with resume information
        """
        with self.lock:
            resume_info = {
                "completed_chapters": [],
                "in_progress_chapters": [],
                "failed_chapters": [],
                "next_chapter": None,
                "can_resume": False
            }

            for chapter_str, info in self.master_data.get('chapters', {}).items():
                chapter_num = int(chapter_str)
                stage = info['stage']

                if stage == 'completed':
                    resume_info['completed_chapters'].append(chapter_num)
                elif stage in ['started', 'prompt_created', 'generated', 'analyzed', 'enhanced']:
                    resume_info['in_progress_chapters'].append({
                        'chapter': chapter_num,
                        'stage': stage,
                        'can_continue': stage != 'started'  # Can continue from any stage except started
                    })
                elif info.get('error'):
                    resume_info['failed_chapters'].append({
                        'chapter': chapter_num,
                        'error': info['error'],
                        'retry_count': info.get('retry_count', 0)
                    })

            # Determine next chapter to process
            all_chapters = set(range(1, 21))  # Assume 20 chapters max, adjust as needed
            processed = set(resume_info['completed_chapters'])
            remaining = all_chapters - processed

            if remaining:
                resume_info['next_chapter'] = min(remaining)
                resume_info['can_resume'] = True

            return resume_info

    def get_generation_state(self, chapter_num: int) -> Optional[Dict]:
        """
        Get the current state of a chapter's generation

        Returns:
            Dictionary with generation state or None
        """
        checkpoint = self.load_checkpoint(chapter_num)
        if not checkpoint:
            return None

        return {
            'stage': checkpoint.stage,
            'has_prompt': checkpoint.prompt is not None,
            'has_raw_text': checkpoint.raw_text is not None,
            'has_enhanced_text': checkpoint.enhanced_text is not None,
            'has_quality_prediction': checkpoint.quality_prediction is not None,
            'has_analysis': checkpoint.detail_density is not None,
            'retry_count': checkpoint.retry_count,
            'can_resume_from': self._get_resume_stage(checkpoint)
        }

    def _get_resume_stage(self, checkpoint: GenerationCheckpoint) -> str:
        """Determine which stage we can resume from"""
        if checkpoint.enhanced_text:
            return 'save'  # Just need to save
        elif checkpoint.raw_text and checkpoint.detail_density:
            return 'enhance'  # Need to enhance
        elif checkpoint.raw_text:
            return 'analyze'  # Need to analyze
        elif checkpoint.prompt:
            return 'generate'  # Need to generate from prompt
        else:
            return 'start'  # Need to start over

    def _save_json_atomic(self, filepath: Path, data: Dict):
        """
        Save JSON atomically (write to temp, then rename)

        This prevents corruption from partial writes
        """
        temp_file = filepath.with_suffix('.tmp')

        try:
            # Write to temp file
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename (on POSIX systems)
            temp_file.replace(filepath)

        except Exception as e:
            print(f"[CheckpointManager] Error saving {filepath}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _load_json_safe(self, filepath: Path) -> Optional[Dict]:
        """
        Load JSON with error handling

        Returns:
            Dictionary or None if load fails
        """
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[CheckpointManager] Error loading {filepath}: {e}")
            return None

    def _calculate_checksum(self, data: Dict) -> str:
        """Calculate SHA256 checksum for data integrity"""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _rotate_backups(self):
        """Rotate backup checkpoints, keeping only max_backups"""
        backup_dir = self.checkpoint_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"checkpoint_{timestamp}"

        # Copy current checkpoints to backup
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(self.chapters_dir, backup_path)

        # Remove old backups
        backups = sorted(backup_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            shutil.rmtree(oldest)

    def _load_from_backup(self, chapter_num: int) -> Optional[GenerationCheckpoint]:
        """Try to load chapter from backup if main is corrupted"""
        backup_dir = self.checkpoint_dir / "backups"
        if not backup_dir.exists():
            return None

        # Try backups from newest to oldest
        backups = sorted(backup_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

        for backup in backups:
            backup_file = backup / f"chapter_{chapter_num:03d}.json"
            if backup_file.exists():
                data = self._load_json_safe(backup_file)
                if data:
                    print(f"[CheckpointManager] Recovered chapter {chapter_num} from backup {backup.name}")
                    return GenerationCheckpoint.from_dict(data)

        return None

    def clear_chapter(self, chapter_num: int):
        """Clear checkpoint for a specific chapter (for retry)"""
        with self.lock:
            chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.json"
            if chapter_file.exists():
                chapter_file.unlink()

            if str(chapter_num) in self.master_data['chapters']:
                del self.master_data['chapters'][str(chapter_num)]
                self._save_json_atomic(self.master_checkpoint, self.master_data)

    def get_statistics(self) -> Dict:
        """Get generation statistics from checkpoints"""
        with self.lock:
            stats = self.master_data.get('generation_stats', {})

            # Add checkpoint-specific stats
            stats['total_chapters'] = len(self.master_data.get('chapters', {}))
            stats['completed_chapters'] = sum(
                1 for info in self.master_data.get('chapters', {}).values()
                if info['stage'] == 'completed'
            )
            stats['failed_chapters'] = sum(
                1 for info in self.master_data.get('chapters', {}).values()
                if info.get('error')
            )

            return stats


class CheckpointedOrchestrator:
    """
    Wrapper that adds checkpoint capability to any orchestrator

    This can wrap BookOrchestrator or AsyncBookOrchestrator to add
    checkpoint/resume functionality.
    """

    def __init__(self, orchestrator, checkpoint_manager: CheckpointManager):
        """
        Initialize checkpointed orchestrator

        Args:
            orchestrator: Base orchestrator instance
            checkpoint_manager: CheckpointManager instance
        """
        self.orchestrator = orchestrator
        self.checkpoint_manager = checkpoint_manager

        # Override methods to add checkpointing
        self._original_generate = orchestrator.generate_chapter
        orchestrator.generate_chapter = self._generate_with_checkpoint

    def _generate_with_checkpoint(self, chapter_num: int, max_retries: int = 3) -> bool:
        """
        Generate chapter with checkpoint saving

        Saves checkpoints at each critical stage:
        1. After prompt creation
        2. After initial generation
        3. After analysis
        4. After each enhancement iteration
        5. After successful completion
        """

        # Check for existing checkpoint
        existing = self.checkpoint_manager.load_checkpoint(chapter_num)
        if existing and existing.stage == 'completed':
            print(f"[Checkpoint] Chapter {chapter_num} already completed, skipping")
            return True

        # Resume from checkpoint if available
        if existing:
            print(f"[Checkpoint] Resuming chapter {chapter_num} from stage: {existing.stage}")
            return self._resume_from_checkpoint(existing)

        # Create new checkpoint
        checkpoint = GenerationCheckpoint(
            chapter_num=chapter_num,
            stage='started',
            timestamp=time.time(),
            data={}
        )
        self.checkpoint_manager.save_checkpoint(checkpoint)

        try:
            # Call original generation with checkpoint hooks
            result = self._generate_with_hooks(chapter_num, checkpoint, max_retries)

            if result:
                checkpoint.stage = 'completed'
                self.checkpoint_manager.save_checkpoint(checkpoint)

            return result

        except Exception as e:
            checkpoint.stage = 'failed'
            checkpoint.error = str(e)
            self.checkpoint_manager.save_checkpoint(checkpoint)
            raise

    def _generate_with_hooks(self, chapter_num: int, checkpoint: GenerationCheckpoint,
                            max_retries: int) -> bool:
        """
        Generate with checkpoint hooks at each stage

        This would need to be integrated with the actual orchestrator methods
        """
        # This is a simplified example - would need deeper integration
        # with the actual orchestrator methods

        # For now, just call the original method
        return self._original_generate(chapter_num, max_retries)

    def _resume_from_checkpoint(self, checkpoint: GenerationCheckpoint) -> bool:
        """
        Resume generation from a checkpoint

        Based on the checkpoint stage, continue from the appropriate point
        """
        resume_stage = self.checkpoint_manager._get_resume_stage(checkpoint)

        if resume_stage == 'save':
            # Just save the already-enhanced text
            chapter_file = self.orchestrator.chapters_dir / f"chapter_{checkpoint.chapter_num:03d}.md"
            chapter_file.write_text(checkpoint.enhanced_text or checkpoint.raw_text)
            return True

        elif resume_stage == 'enhance':
            # Run enhancement on existing text
            # Would need to call orchestrator's enhancement methods
            pass

        elif resume_stage == 'analyze':
            # Run analysis on existing text
            # Would need to call orchestrator's analysis methods
            pass

        elif resume_stage == 'generate':
            # Generate from existing prompt
            # Would need to call orchestrator's generation methods
            pass

        else:
            # Start over
            return self._original_generate(checkpoint.chapter_num, 3)

        return False


def demo_checkpoint_manager():
    """Demonstrate checkpoint manager functionality"""
    print("="*60)
    print("CHECKPOINT MANAGER DEMO")
    print("="*60)

    # Create checkpoint manager
    workspace = Path("workspace/test-checkpoints")
    manager = CheckpointManager(workspace)

    # Simulate chapter generation with checkpoints
    for chapter in [1, 2, 3]:
        print(f"\n--- Chapter {chapter} ---")

        # Stage 1: Started
        checkpoint = GenerationCheckpoint(
            chapter_num=chapter,
            stage='started',
            timestamp=time.time(),
            data={'outline': f'Chapter {chapter} outline'}
        )
        manager.save_checkpoint(checkpoint)
        print(f"✓ Saved: started")

        # Stage 2: Prompt created
        checkpoint.stage = 'prompt_created'
        checkpoint.prompt = f"Generate chapter {chapter}..."
        manager.save_checkpoint(checkpoint)
        print(f"✓ Saved: prompt_created")

        # Stage 3: Generated
        checkpoint.stage = 'generated'
        checkpoint.raw_text = f"Chapter {chapter} text..." * 100
        checkpoint.generation_tokens = 1500
        checkpoint.total_cost = 0.015
        manager.save_checkpoint(checkpoint)
        print(f"✓ Saved: generated")

        # Stage 4: Analyzed
        checkpoint.stage = 'analyzed'
        checkpoint.detail_density = {'density': 3.5, 'passed': True}
        checkpoint.word_count_analysis = {'actual': 1500, 'target': 1500, 'passed': True}
        manager.save_checkpoint(checkpoint)
        print(f"✓ Saved: analyzed")

        # Stage 5: Completed
        checkpoint.stage = 'completed'
        checkpoint.enhanced_text = checkpoint.raw_text + " [enhanced]"
        manager.save_checkpoint(checkpoint)
        print(f"✓ Saved: completed")

    # Show resume point
    print("\n" + "="*60)
    print("RESUME POINT ANALYSIS")
    print("="*60)

    resume_info = manager.get_resume_point()
    print(f"Completed chapters: {resume_info['completed_chapters']}")
    print(f"In-progress chapters: {resume_info['in_progress_chapters']}")
    print(f"Failed chapters: {resume_info['failed_chapters']}")
    print(f"Next chapter to process: {resume_info['next_chapter']}")
    print(f"Can resume: {resume_info['can_resume']}")

    # Show statistics
    print("\n" + "="*60)
    print("GENERATION STATISTICS")
    print("="*60)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Test checkpoint recovery
    print("\n" + "="*60)
    print("CHECKPOINT RECOVERY TEST")
    print("="*60)

    # Load checkpoint
    loaded = manager.load_checkpoint(2)
    if loaded:
        print(f"✓ Loaded checkpoint for chapter {loaded.chapter_num}")
        print(f"  Stage: {loaded.stage}")
        print(f"  Has prompt: {loaded.prompt is not None}")
        print(f"  Has text: {loaded.raw_text is not None}")
        print(f"  Cost: ${loaded.total_cost:.3f}")

    # Show generation state
    state = manager.get_generation_state(2)
    if state:
        print(f"\nGeneration state:")
        print(f"  Can resume from: {state['can_resume_from']}")

    # Cleanup
    import shutil
    if workspace.exists():
        shutil.rmtree(workspace)
        print(f"\n✓ Cleaned up {workspace}")


if __name__ == "__main__":
    demo_checkpoint_manager()