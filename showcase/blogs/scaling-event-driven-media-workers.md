---
title: "Dev Log: Decoupling Media Workers and Eliminating Web Process OOM at 5,000-User Scale"
slug: "scaling-event-driven-media-workers"
topic: "event-driven-worker-scalability-and-oom-isolation"
date: "2026-10-10"
status: "Published"
tags: ["fastapi", "workers", "event-driven", "oom", "disk-isolation", "concurrency", "retry-backoff", "dev-log"]
references:
  - "ai-directed-learning/contentgen-services/app/entrypoints/video_worker.py"
  - "ai-directed-learning/contentgen-services/app/entrypoints/audio_worker.py"
  - "ai-directed-learning/contentgen-services/app/core/retry.py:10-97"
  - "ai-directed-learning/documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md"
---

# Dev Log: Decoupling Media Workers and Eliminating Web Process OOM at 5,000-User Scale

**Project**: `ai-directed-learning`  
**Source Ref**: [`contentgen-services/app/entrypoints/video_worker.py`](file:///Users/anupmanekar/DevWorkspace/ai-directed-learning/contentgen-services/app/entrypoints/video_worker.py), [`contentgen-services/app/core/retry.py:10-97`](file:///Users/anupmanekar/DevWorkspace/ai-directed-learning/contentgen-services/app/core/retry.py#L10-L97)  
**Docs**: [`documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md`](file:///Users/anupmanekar/DevWorkspace/ai-directed-learning/documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md)  

---

## What Broke

Simulating 5,000 concurrent students generating personalized course modules caused immediate outages across `contentgen-services/`:

1. **FastAPI Web Server OOM Crashes**: `AudioWorker` and `VideoWorker` ran as background daemon threads directly inside the FastAPI ASGI process (`threading.Thread(target=worker.run, daemon=True)`). High concurrent jobs triggered simultaneous FFmpeg rendering pipelines, frame buffers, and audio stitching in-process. Memory breached container limits (SIGKILL / Exit code 137), taking down the HTTP gateway and dropping all in-flight requests.
2. **`/tmp` File Collisions and Disk Leaks**: Workers dumped intermediate `.mp4` chunks and `.wav` audio slices directly into `/tmp` using static or semi-predictable paths. Concurrent threads stepped on each other's temporary files, generating corrupt video artifacts. When workers crashed midway through rendering, temporary files were never deleted, exhausting disk space on the host root partition.
3. **Upstream TTS Rate Limit Lockout (HTTP 429)**: Bursts of requests to external TTS engines (Sarvam AI for Indian regional languages and Google TTS) hit provider rate limits simultaneously. Uncoordinated retries created a thundering herd, guaranteeing repeated 429 rejections.

---

## Why It Broke

- **Colocated Monolithic Concurrency**: Running memory-intensive media processing inside an ASGI web process violates process isolation. FFmpeg allocations and unbounded thread pools will exhaust memory and kill the web server.
- **Shared Temporary File Namespace**: Writing intermediate chunks directly to shared `/tmp` paths without per-job directory isolation creates race conditions under concurrent execution. Skipping cleanup in exception paths leaks disk space.
- **Synchronized Retries**: Retrying third-party API calls without exponential backoff and randomized jitter synchronizes subsequent requests into identical time buckets, overwhelming rate-limited upstream token buckets.

---

## The Fix & Code Reference

### 1. Decoupling Web API from Standalone Worker Entrypoints (`app/entrypoints/video_worker.py`)

Workers were removed from the FastAPI web server lifecycle and decoupled into dedicated standalone processes. Per engineering conventions ("scripts are for utilities only, use a proper enclosing folder"), production daemons were placed into `app/entrypoints/` instead of `scripts/`:

- `contentgen-services/app/entrypoints/audio_worker.py`
- `contentgen-services/app/entrypoints/video_worker.py`

The FastAPI web service only validates requests and publishes task IDs to the queue. Standalone worker processes consume jobs independently under dedicated container resource limits:

```python
# contentgen-services/app/entrypoints/video_worker.py:1-42
import os
import shutil
import tempfile
import uuid
import logging
from app.core.retry import retry_with_backoff, is_transient_error

logger = logging.getLogger(__name__)

class VideoWorker:
    def __init__(self, queue_client=None):
        self.queue = queue_client

    def process_job(self, job_data: dict) -> str:
        job_id = job_data.get("id", uuid.uuid4().hex)
        # Ephemeral disk isolation: isolated scratch directory per job
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

    def consume_loop(self):
        logger.info("VideoWorker listening for jobs...")
        # Polling/subscription loop running in standalone process container
        ...

def main():
    worker = VideoWorker()
    worker.consume_loop()

if __name__ == "__main__":
    main()
```

### 2. Ephemeral Scratch Isolation with Guaranteed Cleanup

Every worker job allocates a dedicated temporary directory with `tempfile.mkdtemp(prefix=f"vid_{job_id[:8]}_")`. All intermediate FFmpeg slices, audio tracks, and slide images live exclusively inside this directory. Cleanup is guaranteed via a `finally:` block with `shutil.rmtree(temp_dir, ignore_errors=True)`, ensuring 0 leaked files on uncaught errors or timeouts.

### 3. Jittered Exponential Backoff for Upstream 429s (`app/core/retry.py:10-97`)

Implemented `@retry_with_backoff` in `contentgen-services/app/core/retry.py:10-97` to handle rate limits and transient 5xx errors from Sarvam AI and Google TTS:

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

Applied to the TTS synthesis pipeline:

```python
# contentgen-services/app/entrypoints/audio_worker.py:38-48
@retry_with_backoff(
    max_retries=5,
    base_delay=1.5,
    max_delay=20.0,
    predicate=is_transient_error
)
def synthesize_tts_chunk(self, text: str, language: str) -> bytes:
    return self.sarvam_client.synthesize(text=text, language_code=language)
```

---

## Notes & Takeaways

- **Web Server is a Dispatcher Only**: Never run compute-heavy tasks or FFmpeg subprocesses inside web process threads. Isolate heavy workers behind message queues in dedicated containers.
- **Entrypoint Directory Discipline**: Production daemons belong in `app/entrypoints/`, not in `scripts/`. Keep `scripts/` strictly for manual dev tools and DB migrations.
- **Zero-Shared Scratch Disks**: Every media render job must run in an isolated `mkdtemp` folder cleaned via `try...finally`. Shared paths will fail under high concurrency.
- **Jitter Prevents Re-Collision**: Exponential backoff without jitter fails against rate-limited APIs because parallel requests back off by identical durations and collide again. Full jitter desynchronizes the retries.
