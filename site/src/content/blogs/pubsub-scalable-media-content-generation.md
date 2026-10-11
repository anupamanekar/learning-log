---
title: "Dev Log: Scaling Audio & Video Generation via Pub/Sub Event Decoupling"
slug: "scaling-media-generation-with-pubsub"
project: "adaptive-edtech-platform"
topic: "pubsub-event-driven-media-generation-scalability"
date: "2026-10-10"
status: "Published"
tags: ["pubsub", "fastapi", "workers", "event-driven", "ffmpeg", "scalability", "concurrency", "dev-log"]
references:
  - "contentgen-services/app/services/pubsub_client.py:67-133"
  - "contentgen-services/app/api/content.py:454-465"
  - "contentgen-services/app/api/content.py:664-676"
  - "contentgen-services/app/entrypoints/video_worker.py:43-104"
  - "documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md:7-34"
---

# Dev Log: Scaling Audio & Video Generation via Pub/Sub Event Decoupling

**Project**: `adaptive-edtech-platform`  
**Source Ref**: [`contentgen-services/app/services/pubsub_client.py:67-133`](contentgen-services/app/services/pubsub_client.py#L67-L133)  
**API Code**: [`contentgen-services/app/api/content.py:664-676`](contentgen-services/app/api/content.py#L664-L676)  
**Worker Entrypoint**: [`contentgen-services/app/entrypoints/video_worker.py:43-104`](contentgen-services/app/entrypoints/video_worker.py#L43-L104)

---

## What Broke

Our course generation service (`contentgen-services/`) renders slide graphics with Pillow, calls external speech synthesis APIs (Sarvam AI / Google TTS), and compiles `.mp4` video lessons with FFmpeg. A single module takes 30s to 120s to render.

Under concurrent usage, running these jobs in-process or synchronously inside the FastAPI container caused three critical failures:
1. **API Ingress Timeouts**: Client HTTP connections timed out waiting for 60s+ audio/video compilation tasks.
2. **Web Container OOM Panics**: Concurrent FFmpeg CLI executions and Pillow canvas bitmaps exceeded the container's 1GB memory limit, triggering Linux OOM killer (`SIGKILL / Exit 137`) and terminating unrelated active web requests.
3. **Dropped In-Flight Jobs**: Any web container restart or deployment killed ongoing rendering threads with zero recovery mechanism.

---

## Why It Failed

Coupling CPU- and memory-heavy subprocesses (FFmpeg) with an ASGI web server created resource contention. Every new generation request immediately degraded API response latency for all users. Without an asynchronous message broker, traffic spikes directly resulted in server resource exhaustion.

---

## The Fix: Event-Driven Queue & Decoupled Workers

We decoupled media composition from the FastAPI web server using Google Cloud Pub/Sub and isolated worker pods:

```
[Client App]
     │ (POST /generate-video)
     ▼
[FastAPI Web Server (Port 8001)] 
     │
     ├─► [Writes Initial Job State to Firestore]
     └─► [Publishes Message to Pub/Sub Topic: video-jobs]
           │
           ▼
     [GCP Pub/Sub Queue (Buffer & At-Least-Once Delivery)]
           │
           ▼ (StreamingPull)
     [Isolated VideoWorker Pod] ──► [FFmpeg Subprocess] ──► [Upload MP4 to GCS]
           │
           └─► [Real-Time Progress Updates] ──► [Firestore] ──► [Client onSnapshot]
```

### 1. Non-Blocking Fast Publisher in FastAPI

The HTTP endpoint creates a tracking document in Firestore, pushes a task message to the Pub/Sub topic, and immediately returns HTTP 202 to the client in `<40ms`:

```python
# contentgen-services/app/api/content.py:664-676
# 3. Create job tracking record in Firestore
job = await video_job_repo.create(
    generated_content_id=content_id,
    total_slides=len(slides),
    background_image=background_image,
    target_languages=target_languages,
)

# 4. Offload task to Pub/Sub topic asynchronously
try:
    pubsub = get_pubsub_client()
    pubsub.publish_video_job(
        content_id, 
        total_slides=len(slides),
        background_image=background_image,
        target_languages=target_languages,
    )
except Exception as pub_err:
    logger.warning(f"Pub/Sub publish failed: {pub_err} — job will need manual trigger")
```

### 2. Standalone Consumer Worker with Signal Trapping

Workers run in independent container entrypoints (`app/entrypoints/video_worker.py`). The worker pulls from the Pub/Sub subscription using `StreamingPullFuture` and safely bridges synchronous message callbacks into an `asyncio` execution loop:

```python
# contentgen-services/app/entrypoints/video_worker.py:74-103
def _subscriber_callback(message):
    """Sync wrapper that bridges Pub/Sub callback to async handler."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(worker.process_video_job(message))
    finally:
        loop.close()

# Subscribe to video jobs topic
streaming_pull_future = pubsub_client.subscribe_video_jobs(_subscriber_callback)

try:
    while not shutdown_requested:
        try:
            streaming_pull_future.result(timeout=5)
        except TimeoutError:
            pass  # Expected timeout while waiting for messages
finally:
    streaming_pull_future.cancel()
    streaming_pull_future.result()
    logger.info("Worker shutdown complete")
```

### 3. Out-of-Band Real-Time Progress via Firestore

The worker writes incremental status updates (`slides_rendered`, `percent_complete`) directly to Firestore. The web server is completely bypassed for status polling; the frontend listens to real-time Firestore document updates via `onSnapshot`.

---

## Notes & Edge Cases

- **At-Least-Once Delivery & Idempotency**: Pub/Sub guarantees at-least-once delivery. If an FFmpeg worker crashes before acknowledging (`message.ack()`), the message is redelivered. Workers check existing Firestore job state before re-running synthesis to prevent duplicate billing.
- **Independent Pod Scaling**: The web server stays lean on 512MB RAM pods, while rendering workers run on 2GB–4GB pods that can autoscale based on Pub/Sub unacknowledged message depth (`num_undelivered_messages`).
- **Disk Isolation**: Workers allocate unique UUID directories (`tempfile.mkdtemp`) for each task and guarantee cleanup with `finally: shutil.rmtree(temp_dir)` to prevent ephemeral disk saturation.
