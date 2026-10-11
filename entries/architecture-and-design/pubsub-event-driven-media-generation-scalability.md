---
id: "pubsub-event-driven-media-generation-scalability"
title: "Scaling Multimedia Generation via Cloud Pub/Sub and Decoupled Worker Pods"
project: "adaptive-edtech-platform"
date: "2026-10-10"
category: "architecture-and-design"
tags: ["pubsub", "event-driven", "workers", "fastapi", "scalability", "ffmpeg", "firestore", "concurrency"]
severity_or_impact: "Critical"
showcase_potential: "Blog"
status: "Showcase Drafted"
source_references:
  - "contentgen-services/app/services/pubsub_client.py:67-133"
  - "contentgen-services/app/api/content.py:454-465"
  - "contentgen-services/app/api/content.py:664-676"
  - "contentgen-services/app/entrypoints/video_worker.py:43-104"
  - "documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md:7-34"
---

# Scaling Multimedia Generation via Cloud Pub/Sub and Decoupled Worker Pods

## Problem
Generating multimodal learning content (slide rendering via Pillow, speech synthesis via Google TTS / Sarvam AI, and video composition via FFmpeg) takes between 25s and 120s per course module. 

Under concurrent usage (such as a classroom batch generating courses simultaneously), synchronously executing or tracking jobs inside the FastAPI web server caused catastrophic failures:
1. **HTTP Gateway Timeouts (504s)**: Long-running synthesis tasks tied up ASGI request-response threads, exceeding ingress timeout windows.
2. **Web Container OOM Collisions**: Spawning FFmpeg subprocesses and Pillow canvas buffers in background threads inside the FastAPI container exhausted memory limits, killing the web process and terminating unrelated active HTTP sessions.
3. **Thundering Herd & Job Loss**: Any container restart or crash mid-generation permanently dropped in-flight tasks with no retry queue.

## Root Cause
Coupling CPU/memory-bound rendering tasks (FFmpeg / audio processing) with the I/O-bound web server process created resource contention. Without an asynchronous message queue, spikes in generation requests immediately translated into concurrency spikes on container memory and thread pools.

## Solution & Code
The architecture was refactored into an event-driven pub/sub model decoupling the web server from processing workers:

```
[FastAPI REST Server (Port 8001)]
       │
       ├─► [Writes Initial Job State to Firestore]
       └─► [Publishes Job Event to Google Cloud Pub/Sub]
             │
             ├──► Topic: audio-jobs ──► [AudioWorker Pods (StreamingPull)]
             └──► Topic: video-jobs ──► [VideoWorker Pods (StreamingPull)]
```

### 1. Fast Non-Blocking Publish in API Layer
FastAPI endpoints persist initial state to Firestore and publish an event to GCP Pub/Sub, returning HTTP 202 to the client in `<40ms`:

```python
# contentgen-services/app/api/content.py:664-676
# 3. Create job tracking record in Firestore
job = await video_job_repo.create(
    generated_content_id=content_id,
    total_slides=len(slides),
    background_image=background_image,
    target_languages=target_languages,
)

# 4. Asynchronously offload task to Pub/Sub
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

### 2. Standalone Consumer Entrypoint with Graceful Shutdown
Dedicated worker processes consume from Pub/Sub subscriptions via `StreamingPullFuture`, bridging synchronous pull callbacks into `asyncio` loops and handling POSIX signals:

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

### 3. Out-of-Band State Synchronization via Firestore
Workers update granular rendering milestones (e.g. `slides_rendered`, `audio_synthesized`, `progress_percent`) directly to Firestore documents (`video_jobs/{id}`). The client frontend listens to Firestore real-time snapshots (`onSnapshot`), eliminating polling load on the web API.

## Key Takeaway
- Decoupling heavy CLI subprocesses (FFmpeg) and external API synthesis behind Pub/Sub queues insulates API servers from OOM crashes and absorbs traffic spikes without dropping jobs.
- Pairing Pub/Sub for task distribution with Firestore for client-side state listeners eliminates the need for polling endpoints on the API server.
