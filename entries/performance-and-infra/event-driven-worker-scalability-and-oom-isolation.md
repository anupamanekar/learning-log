---
id: "event-driven-worker-scalability-and-oom-isolation"
title: "Decoupling In-Process Media Workers, Ephemeral Disk Isolation, and Jittered Retries for 5,000-User Concurrency"
project: "ai-directed-learning"
date: "2026-10-10"
category: "performance-and-infra"
tags: ["fastapi", "workers", "event-driven", "oom", "disk-isolation", "concurrency", "retry-backoff", "ffmpeg", "sarvam-ai", "tts"]
severity_or_impact: "Critical"
showcase_potential: "Blog"
status: "Showcase Drafted"
source_references:
  - "ai-directed-learning/contentgen-services/app/entrypoints/audio_worker.py"
  - "ai-directed-learning/contentgen-services/app/entrypoints/video_worker.py"
  - "ai-directed-learning/contentgen-services/app/core/retry.py:10-97"
  - "ai-directed-learning/documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md"
---

# Decoupling In-Process Media Workers, Ephemeral Disk Isolation, and Jittered Retries for 5,000-User Concurrency

## Problem
During a 5,000 concurrent user load test review on the `ai-directed-learning` multimedia generation service (`contentgen-services/`), the application suffered cascading infrastructure outages:
1. **Web Server Out-Of-Memory (OOM) Crashes**: `AudioWorker` and `VideoWorker` ran as in-process daemon threads inside the FastAPI ASGI web server process (`threading.Thread(target=worker.run, daemon=True)`). High concurrent generation requests triggered memory spikes from FFmpeg video rendering, frame decoding, and audio stitching inside the web container, tripping the container cgroup memory limits (SIGKILL / Exit 137) and dropping all active HTTP client connections.
2. **`/tmp` Filesystem Collisions and Disk Leaks**: Concurrent worker threads wrote intermediate video chunks and wav slices to fixed or pseudo-random shared paths under `/tmp` (e.g. `/tmp/slide_chunk.mp4`). Parallel tasks clobbered each other's temporary media frames, generating corrupted artifacts. Furthermore, when unhandled errors occurred during rendering, cleanup was skipped, saturating the root partition.
3. **Upstream TTS Rate Limit Cascades (HTTP 429)**: Bursts of concurrent synthesis requests to external TTS providers (Sarvam AI for Indian regional voices and Google Cloud TTS) triggered strict rate limits (`HTTP 429 Too Many Requests`). The lack of jittered backoff caused thundering herd retries that repeatedly failed and exhausted API quotas.

## Root Cause
- **Monolithic In-Process Concurrency**: Heavy CPU/memory tasks (video composition, audio encoding) were colocated in the same process space as the HTTP gateway. When media processing spiked memory consumption, the entire web server died.
- **Shared Scratch Namespace**: Temporary file generation lacked per-job directory isolation, and lacked guaranteed cleanup via exception-safe lifecycle blocks.
- **Uncoordinated Burst Retries**: Naive retry loops hit third-party API endpoints in synchronized lockstep, amplifying 429 rate limit errors instead of desynchronizing requests with exponential backoff and randomized jitter.

## Solution & Code

### 1. Decoupling Web API from Standalone Worker Entrypoints
Instead of running workers inside FastAPI background daemon threads, workers were refactored into standalone production processes. Guided by engineering standards ("scripts are for utilities only, use a proper enclosing folder"), worker entrypoints were located in `app/entrypoints/` rather than a loose `scripts/` directory:
- `contentgen-services/app/entrypoints/audio_worker.py`
- `contentgen-services/app/entrypoints/video_worker.py`

The FastAPI web service only enqueues tasks to Redis/message broker. Dedicated worker containers execute the jobs with isolated memory and CPU quotas.

### 2. Ephemeral Scratch Isolation with Guaranteed Cleanup
Each worker process creates an isolated temporary directory per job using `tempfile.mkdtemp` and cleans up in a `finally` block:

```python
# contentgen-services/app/entrypoints/video_worker.py
import os
import shutil
import tempfile
import uuid
import logging
from app.core.retry import retry_with_backoff, is_transient_error

logger = logging.getLogger(__name__)

class VideoWorker:
    def process_job(self, job_data: dict) -> str:
        job_id = job_data.get("id", uuid.uuid4().hex)
        # Unique isolated scratch directory per job prevents file collisions
        temp_dir = tempfile.mkdtemp(prefix=f"vid_{job_id[:8]}_")
        try:
            rendered_path = self._render_video_pipeline(job_data, work_dir=temp_dir)
            final_artifact_path = self._persist_artifact(rendered_path, job_id)
            return final_artifact_path
        finally:
            # Guaranteed cleanup prevents root partition disk exhaustion
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Cleaned up ephemeral scratch dir: {temp_dir}")
```

### 3. Jittered Exponential Backoff for Upstream 429s (`retry.py:10-97`)
Created a reusable backoff decorator in `contentgen-services/app/core/retry.py` featuring a predicate filter for transient errors and randomized jitter to prevent thundering herd collisions:

```python
# contentgen-services/app/core/retry.py:10-97
import time
import random
import logging
import functools
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger(__name__)

def is_transient_error(exc: Exception) -> bool:
    """
    Discriminates transient infrastructure/rate-limit errors from deterministic failures.
    Returns True for 429, 502, 503, 504 and network drops; False for 400, 401, 403, 422.
    """
    status_code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    if status_code in (429, 502, 503, 504):
        return True
    
    msg = str(exc).lower()
    transient_indicators = (
        "rate limit", "too many requests", "timed out", 
        "connection reset", "503 service unavailable"
    )
    return any(indicator in msg for indicator in transient_indicators)

def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter_factor: float = 0.5,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    predicate: Callable[[Exception], bool] = is_transient_error,
):
    """
    Exponential backoff with full randomized jitter and transient error filtering.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    attempt += 1
                    if attempt > max_retries or not predicate(exc):
                        logger.error(f"[{func.__name__}] Fatal or exhausted retries ({attempt}/{max_retries}): {exc}")
                        raise
                    
                    # Exponential backoff + randomized jitter
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, jitter_factor * delay)
                    sleep_time = delay + jitter
                    
                    logger.warning(
                        f"[{func.__name__}] Transient error on attempt {attempt}/{max_retries}: {exc}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
        return wrapper
    return decorator
```

Applied to Sarvam AI and Google TTS callers:

```python
# contentgen-services/app/entrypoints/audio_worker.py
@retry_with_backoff(
    max_retries=5,
    base_delay=1.5,
    max_delay=20.0,
    predicate=is_transient_error
)
def synthesize_tts_chunk(self, text: str, language: str) -> bytes:
    return self.sarvam_client.synthesize(text=text, language_code=language)
```

## Key Takeaway
- **Hard Process Boundary for Heavy Tasks**: Never host multimedia generation, FFmpeg subprocesses, or heavy batch pipelines as daemon threads inside ASGI web servers. Web servers must remain thin dispatchers; heavy compute belongs in standalone worker processes (`app/entrypoints/`) with decoupled cgroup memory limits.
- **Mandatory Ephemeral Scratch Sandboxing**: Always allocate per-job isolated directories (`tempfile.mkdtemp`) and enforce `shutil.rmtree` inside `finally` blocks to prevent concurrency clobbering and disk leaks.
- **Jitter is Mandatory for 429 Resilience**: Exponential backoff without jitter causes synchronized thundering herds. Adding randomized jitter desynchronizes retries and allows upstream rate-limit token buckets (Sarvam / Google TTS) to recover cleanly.
