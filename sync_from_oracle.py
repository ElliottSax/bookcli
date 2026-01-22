#!/usr/bin/env python3
"""
Sync completed books from Oracle Cloud workers to local storage.
Runs as a background process to continuously pull new books.
"""

import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

from lib.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# Configuration
ORACLE_WORKERS = [
    {"ip": "147.224.209.15", "key": "~/.ssh/oci_worker_key", "user": "ubuntu"},
    {"ip": "64.181.220.95", "key": "~/.ssh/oci_worker_key", "user": "ubuntu"},
    {"ip": "170.9.248.244", "key": "~/.ssh/oci_new_worker_key", "user": "ubuntu"},
]
LOCAL_OUTPUT = Path("/mnt/e/projects/bookcli/output/fiction")
SYNC_INTERVAL = 300  # 5 minutes

def sync_worker(worker: dict) -> int:
    """Sync completed books from a single worker."""
    ip = worker["ip"]
    key = os.path.expanduser(worker["key"])
    user = worker["user"]
    
    synced = 0
    
    try:
        # Get list of completed books
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-i", key,
            f"{user}@{ip}",
            "find /home/ubuntu/output/books -name .complete -type f 2>/dev/null"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.warning(f"Failed to list books on {ip}")
            return 0
        
        complete_files = result.stdout.strip().split('\n')
        complete_files = [f for f in complete_files if f]
        
        for complete_file in complete_files:
            book_dir = os.path.dirname(complete_file)
            book_name = os.path.basename(book_dir)
            local_dir = LOCAL_OUTPUT / book_name
            
            # Skip if already synced
            if (local_dir / ".synced").exists():
                continue
            
            logger.info(f"Syncing: {book_name} from {ip}")
            
            # Create local directory
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # Rsync the book
            rsync_cmd = [
                "rsync", "-avz", "--progress",
                "-e", f"ssh -o StrictHostKeyChecking=no -i {key}",
                f"{user}@{ip}:{book_dir}/",
                f"{local_dir}/"
            ]
            rsync_result = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=120)
            
            if rsync_result.returncode == 0:
                # Mark as synced
                (local_dir / ".synced").write_text(f"Synced from {ip} at {datetime.now().isoformat()}")
                synced += 1
                logger.info(f"  Synced successfully: {book_name}")
            else:
                logger.error(f"  Failed to sync: {book_name}")
                logger.error(rsync_result.stderr[:500])
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout connecting to {ip}")
    except Exception as e:
        logger.error(f"Error syncing from {ip}: {e}")
    
    return synced

def get_worker_stats(worker: dict) -> dict:
    """Get statistics from a worker."""
    ip = worker["ip"]
    key = os.path.expanduser(worker["key"])
    user = worker["user"]
    
    try:
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-i", key,
            f"{user}@{ip}",
            "ls /home/ubuntu/output/books 2>/dev/null | wc -l; tail -1 /home/ubuntu/autonomous_pipeline.log 2>/dev/null"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return {
                "ip": ip,
                "books": int(lines[0]) if lines[0].isdigit() else 0,
                "last_activity": lines[1] if len(lines) > 1 else "unknown"
            }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.debug(f"Could not get stats from {ip}: {e}")

    return {"ip": ip, "books": 0, "last_activity": "unreachable"}

def run_sync_loop():
    """Run the sync loop forever."""
    logger.info("=" * 60)
    logger.info("ORACLE CLOUD SYNC STARTED")
    logger.info(f"Workers: {[w['ip'] for w in ORACLE_WORKERS]}")
    logger.info(f"Local output: {LOCAL_OUTPUT}")
    logger.info(f"Sync interval: {SYNC_INTERVAL}s")
    logger.info("=" * 60)
    
    total_synced = 0
    
    while True:
        try:
            logger.info("-" * 40)
            
            # Get stats from workers
            for worker in ORACLE_WORKERS:
                stats = get_worker_stats(worker)
                logger.info(f"Worker {stats['ip']}: {stats['books']} books, {stats['last_activity'][:50]}")
            
            # Sync from each worker
            for worker in ORACLE_WORKERS:
                synced = sync_worker(worker)
                total_synced += synced
                if synced > 0:
                    logger.info(f"Synced {synced} books from {worker['ip']} (total: {total_synced})")
            
            # Count local books
            local_books = len([d for d in LOCAL_OUTPUT.iterdir() if d.is_dir()])
            logger.info(f"Local library: {local_books} books")
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
        
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    run_sync_loop()
