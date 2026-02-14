#!/usr/bin/env python3
"""
BookCLI Universal Worker
=========================
Single-file worker that runs on any platform (OCI, VPS, GitHub Actions, Colab).
Connects to the central BookCLI server, claims jobs, processes them via LLM APIs.

Requirements:
    pip install aiohttp

Environment variables:
    BOOKCLI_SERVER   - Server URL (e.g. https://bookcli.example.com)
    BOOKCLI_API_KEY  - Auth token (optional if server has no key)
    PROVIDER         - Which LLM provider to use (default: groq)
    WORKER_ID        - Unique worker ID (auto-generated if not set)
    MAX_RUNTIME      - Max seconds to run before clean exit (default: 0 = forever)

    API keys (set the one matching your PROVIDER):
    GITHUB_TOKEN, TOGETHER_API_KEY, OPENROUTER_API_KEY, DEEPSEEK_API_KEY,
    CEREBRAS_API_KEY, GROQ_API_KEY, HUGGINGFACE_API_KEY, CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ACCOUNT_ID
"""

import asyncio
import json
import logging
import os
import re
import signal
import socket
import sys
import time
from typing import Optional

import aiohttp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVER_URL = os.environ.get("BOOKCLI_SERVER", "http://localhost:8765").rstrip("/")
API_KEY = os.environ.get("BOOKCLI_API_KEY", "")
PROVIDER = os.environ.get("PROVIDER", "groq")
WORKER_ID = os.environ.get(
    "WORKER_ID",
    f"{PROVIDER}-{socket.gethostname()}-{os.getpid()}",
)
MAX_RUNTIME = int(os.environ.get("MAX_RUNTIME", "0"))  # 0 = forever
HEARTBEAT_INTERVAL = 60  # seconds
IDLE_POLL_INTERVAL = 30  # seconds between polls when no work available

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{WORKER_ID}] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("worker")

# ---------------------------------------------------------------------------
# Provider definitions (from launch_workers.py, battle-tested)
# ---------------------------------------------------------------------------
PROVIDERS = {
    "github": {
        "url": "https://models.inference.ai.azure.com/chat/completions",
        "model": "gpt-4o-mini",
        "env_key": "GITHUB_TOKEN",
        "rpm": 5,
        "max_tokens": 8192,
    },
    "together": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "rpm": 60,
        "max_tokens": 4096,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "env_key": "OPENROUTER_API_KEY",
        "rpm": 20,
        "max_tokens": 4096,
        "extra_headers": {
            "HTTP-Referer": "https://bookcli.local",
            "X-Title": "BookCLI Worker",
        },
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "rpm": 60,
        "max_tokens": 8192,
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "llama-3.3-70b",
        "env_key": "CEREBRAS_API_KEY",
        "rpm": 30,
        "max_tokens": 8192,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "rpm": 30,
        "max_tokens": 8192,
    },
    "huggingface": {
        "url": "https://router.huggingface.co/together/v1/chat/completions",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "HUGGINGFACE_API_KEY",
        "rpm": 15,
        "max_tokens": 4096,
    },
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-70b-instruct",
        "model": "@cf/meta/llama-3.1-70b-instruct",
        "env_key": "CLOUDFLARE_API_TOKEN",
        "rpm": 50,
        "max_tokens": 4096,
        "cloudflare": True,
    },
}

# ---------------------------------------------------------------------------
# System prompt (from launch_workers.py)
# ---------------------------------------------------------------------------
FIX_SYSTEM_PROMPT = """You are an expert literary editor specializing in transforming AI-generated prose into exceptional, publication-quality fiction.

Your task is to rewrite the provided chapter to achieve EXCEPTIONAL literary quality while preserving:
- The exact plot and story events
- Character names and relationships
- Setting and worldbuilding details
- The author's intended voice and tone

CRITICAL RULES:
1. NEVER add explanations, comments, or meta-text
2. NEVER use phrases like "Here is the rewritten chapter"
3. Output ONLY the improved chapter text
4. Preserve all markdown formatting (# headers, etc.)
5. Keep the same chapter structure and length (within 20%)

QUALITY STANDARDS:
- Replace ALL "AI-isms" (delve, embark, tapestry, symphony, palpable, couldn't help but, found herself)
- Convert ALL "telling" to "showing" (emotions through action, not labels)
- Eliminate filter words (felt, seemed, noticed, realized, saw, heard)
- Use strong, specific verbs instead of weak ones
- Create vivid sensory details without purple prose
- Ensure natural dialogue with character-specific voices
- Vary sentence structure and rhythm
- Build tension through pacing, not adjectives"""

GENERATE_SYSTEM_PROMPT = """You are an expert fiction author. Write a complete, high-quality chapter based on the provided specification.

CRITICAL RULES:
1. Output ONLY the chapter text, no meta-commentary
2. Write at least 2500 words
3. Use vivid, specific prose - no AI cliches
4. Show, don't tell - convey emotion through action and dialogue
5. Each chapter should have a clear arc with tension and resolution"""


# ---------------------------------------------------------------------------
# LLM API call (from launch_workers.py, handles all edge cases)
# ---------------------------------------------------------------------------
async def call_api(
    session: aiohttp.ClientSession,
    config: dict,
    system_prompt: str,
    user_prompt: str,
) -> Optional[str]:
    api_key = os.getenv(config["env_key"])
    if not api_key:
        logger.error(f"No API key for {config['env_key']}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    headers.update(config.get("extra_headers", {}))

    if config.get("cloudflare"):
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        url = config["url"].format(account_id=account_id)
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": config["max_tokens"],
            "temperature": 0.7,
        }
    else:
        url = config["url"]
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": config["max_tokens"],
            "temperature": 0.7,
        }

    try:
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=180),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if config.get("cloudflare"):
                    return (data.get("result", {}).get("response") or "").strip() or None
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                ) or None
            elif resp.status == 429:
                text = await resp.text()
                wait = 60
                m = re.search(r"wait (\d+) seconds", text)
                if m:
                    wait = int(m.group(1)) + 2
                logger.warning(f"Rate limited, waiting {wait}s")
                await asyncio.sleep(wait)
                return None
            elif resp.status == 402:
                logger.error("Out of credits (402) - provider exhausted")
                return None
            else:
                text = await resp.text()
                logger.warning(f"API {resp.status}: {text[:200]}")
                return None
    except asyncio.TimeoutError:
        logger.warning("Request timed out (180s)")
        return None
    except Exception as e:
        logger.warning(f"Request error: {e}")
        return None


# ---------------------------------------------------------------------------
# Job processing
# ---------------------------------------------------------------------------
async def process_fix_job(
    session: aiohttp.ClientSession, config: dict, job: dict
) -> Optional[str]:
    """Fix a chapter's quality using LLM."""
    content = job.get("content", "")
    if not content or len(content.strip()) < 100:
        return content  # Nothing to fix

    user_prompt = (
        f"Rewrite this chapter to exceptional literary quality. "
        f"Output ONLY the improved chapter text with no preamble or explanation.\n\n"
        f"CHAPTER {job.get('chapter_num', '?')}:\n\n{content}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        if attempt > 0:
            wait = min(30, 5 * (2 ** attempt))
            logger.info(f"Retry {attempt}/{max_retries-1} (waiting {wait}s)")
            await asyncio.sleep(wait)

        result = await call_api(session, config, FIX_SYSTEM_PROMPT, user_prompt)
        if result and len(result) > len(content) * 0.3:
            return result

    return None


async def process_generate_job(
    session: aiohttp.ClientSession, config: dict, job: dict
) -> Optional[str]:
    """Generate a new chapter from spec."""
    spec = job.get("generation_spec", {})
    if not spec:
        return None

    user_prompt = (
        f"Write Chapter {job.get('chapter_num', '?')} of \"{spec.get('title', 'Untitled')}\".\n\n"
        f"Genre: {spec.get('genre', 'Fiction')}\n"
        f"Outline: {spec.get('outline', 'Write a compelling chapter.')}\n"
        f"Total chapters: {spec.get('total_chapters', 12)}\n\n"
        f"Write at least 2500 words. Output ONLY the chapter text."
    )

    result = await call_api(session, config, GENERATE_SYSTEM_PROMPT, user_prompt)
    return result


# ---------------------------------------------------------------------------
# Server communication
# ---------------------------------------------------------------------------
async def claim_job(session: aiohttp.ClientSession) -> Optional[dict]:
    headers = {"X-API-Key": API_KEY, "X-Worker-ID": WORKER_ID}
    try:
        async with session.post(
            f"{SERVER_URL}/jobs/next",
            json={"worker_id": WORKER_ID, "preferred_type": "any", "provider": PROVIDER},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("job")
            else:
                text = await resp.text()
                logger.warning(f"Claim failed ({resp.status}): {text[:100]}")
                return None
    except Exception as e:
        logger.error(f"Server connection error: {e}")
        return None


async def submit_result(session: aiohttp.ClientSession, job_id: int, result: str, latency_ms: float):
    headers = {"X-API-Key": API_KEY}
    config = PROVIDERS[PROVIDER]
    try:
        async with session.post(
            f"{SERVER_URL}/jobs/{job_id}/complete",
            json={
                "worker_id": WORKER_ID,
                "result_content": result,
                "provider": PROVIDER,
                "model": config["model"],
                "latency_ms": latency_ms,
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Submit failed ({resp.status}): {text[:100]}")
    except Exception as e:
        logger.error(f"Submit error: {e}")


async def report_failure(session: aiohttp.ClientSession, job_id: int, error: str):
    headers = {"X-API-Key": API_KEY}
    try:
        async with session.post(
            f"{SERVER_URL}/jobs/{job_id}/fail",
            json={"worker_id": WORKER_ID, "error": error},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            pass
    except Exception:
        pass


async def send_heartbeat(session: aiohttp.ClientSession, job_id: Optional[int]):
    headers = {"X-API-Key": API_KEY}
    try:
        async with session.post(
            f"{SERVER_URL}/jobs/{job_id or 0}/heartbeat",
            json={
                "worker_id": WORKER_ID,
                "status": "working" if job_id else "idle",
                "current_job_id": job_id,
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main worker loop
# ---------------------------------------------------------------------------
async def run():
    config = PROVIDERS.get(PROVIDER)
    if not config:
        logger.error(f"Unknown provider: {PROVIDER}. Available: {', '.join(PROVIDERS.keys())}")
        return

    api_key = os.getenv(config["env_key"])
    if not api_key:
        logger.error(f"No API key set for {config['env_key']}")
        return

    min_interval = 60.0 / config["rpm"]
    running = True
    start_time = time.time()

    def shutdown(sig, frame):
        nonlocal running
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("=" * 50)
    logger.info(f"BookCLI Universal Worker")
    logger.info(f"Server:   {SERVER_URL}")
    logger.info(f"Provider: {PROVIDER} ({config['model']})")
    logger.info(f"Worker:   {WORKER_ID}")
    logger.info(f"RPM:      {config['rpm']} ({min_interval:.1f}s/request)")
    if MAX_RUNTIME:
        logger.info(f"Max runtime: {MAX_RUNTIME}s ({MAX_RUNTIME/60:.0f}min)")
    logger.info("=" * 50)

    # Stats
    jobs_done = 0
    jobs_failed = 0
    total_latency = 0
    consecutive_failures = 0
    max_consecutive_failures = 10
    current_job_id = None

    async with aiohttp.ClientSession() as session:
        # Verify server connection with retry (handles Docker startup ordering)
        server_connected = False
        for attempt in range(12):  # Retry for up to ~2 minutes
            try:
                async with session.get(
                    f"{SERVER_URL}/health",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        logger.info("Server connection OK")
                        server_connected = True
                        break
                    else:
                        logger.warning(f"Server health check returned {resp.status}, retrying...")
            except Exception as e:
                logger.warning(f"Cannot reach server (attempt {attempt + 1}/12): {e}")
            await asyncio.sleep(10)

        if not server_connected:
            logger.error("Failed to connect to server after 12 attempts, exiting")
            return

        # Heartbeat task
        async def heartbeat_loop():
            while running:
                await send_heartbeat(session, current_job_id)
                await asyncio.sleep(HEARTBEAT_INTERVAL)

        heartbeat_task = asyncio.create_task(heartbeat_loop())

        try:
            while running:
                # Check max runtime
                if MAX_RUNTIME and (time.time() - start_time) > MAX_RUNTIME:
                    logger.info(f"Max runtime reached ({MAX_RUNTIME}s), exiting")
                    break

                # Check consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                    break

                # Claim next job
                job = await claim_job(session)
                if not job:
                    consecutive_failures = 0  # No job != failure
                    await asyncio.sleep(IDLE_POLL_INTERVAL)
                    continue

                current_job_id = job["job_id"]
                job_type = job["job_type"]
                logger.info(
                    f"Processing job {job['job_id']}: "
                    f"{job['book_name']}/ch{job.get('chapter_num', '?')} ({job_type})"
                )

                t0 = time.time()
                try:
                    if job_type == "fix_book":
                        result = await process_fix_job(session, config, job)
                    elif job_type == "generate_book":
                        result = await process_generate_job(session, config, job)
                    else:
                        logger.warning(f"Unknown job type: {job_type}")
                        result = None

                    latency_ms = (time.time() - t0) * 1000

                    if result:
                        await submit_result(session, job["job_id"], result, latency_ms)
                        jobs_done += 1
                        total_latency += latency_ms
                        consecutive_failures = 0
                        avg = total_latency / jobs_done
                        logger.info(
                            f"Completed job {job['job_id']} in {latency_ms:.0f}ms "
                            f"(total: {jobs_done}, avg: {avg:.0f}ms)"
                        )
                    else:
                        await report_failure(session, job["job_id"], "LLM returned empty result")
                        jobs_failed += 1
                        consecutive_failures += 1
                        logger.warning(f"Job {job['job_id']} failed: empty result")

                except Exception as e:
                    latency_ms = (time.time() - t0) * 1000
                    await report_failure(session, job["job_id"], str(e))
                    jobs_failed += 1
                    consecutive_failures += 1
                    logger.error(f"Job {job['job_id']} error: {e}")

                finally:
                    current_job_id = None

                # Rate limit
                await asyncio.sleep(min_interval)

        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    # Summary
    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info("WORKER SESSION COMPLETE")
    logger.info(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"Jobs done: {jobs_done}")
    logger.info(f"Jobs failed: {jobs_failed}")
    if jobs_done:
        logger.info(f"Avg latency: {total_latency/jobs_done:.0f}ms")
        logger.info(f"Throughput: {jobs_done/(elapsed/3600):.1f} jobs/hr")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(run())
