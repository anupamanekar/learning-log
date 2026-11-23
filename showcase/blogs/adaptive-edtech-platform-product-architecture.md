---
title: "Dev Log: Adaptive EdTech Platform — Cloud Pub/Sub Decoupled Worker Topology"
slug: "adaptive-edtech-platform-product-architecture"
project: "adaptive-edtech-platform"
topic: "adaptive-edtech-platform-architecture-overview"
date: "2026-11-21"
status: "Published"
tags: ["adaptive-edtech-platform", "architecture", "pubsub", "fastapi", "workers", "ffmpeg", "dev-log"]
references:
  - "contentgen-services/app/services/pubsub_client.py:67-133"
  - "contentgen-services/app/entrypoints/video_worker.py:43-104"
  - "backend/app/domain/models/plan.py"
  - "documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md:7-45"
---

# Dev Log: Adaptive EdTech Platform — Cloud Pub/Sub Decoupled Worker Topology

**Project**: `adaptive-edtech-platform`  
**Pub/Sub Client**: [`contentgen-services/app/services/pubsub_client.py:67-133`](contentgen-services/app/services/pubsub_client.py#L67-L133)  
**Video Worker Entrypoint**: [`contentgen-services/app/entrypoints/video_worker.py:43-104`](contentgen-services/app/entrypoints/video_worker.py#L43-L104)  
**Domain Model**: [`backend/app/domain/models/plan.py`](backend/app/domain/models/plan.py)  

---

## What Happened

As concurrency surged during batch course generation runs, the FastAPI web container suffered repeated Linux OOM crashes (`Exit code 137`) and 504 gateway timeouts. In addition, subscription renewals failed because an early schema design conflated application feature flags with commercial subscription tiers.

---

## Why It Failed

1. **Subprocess Contention in Web Pod**: Running FFmpeg slide encoding and Sarvam AI TTS audio synthesis directly in ASGI request handler threads tied up HTTP connection pools and consumed up to 3.5GB of memory in a 1GB-provisioned container.
2. **Entitlement Coupling**: Storing subscription durations directly on feature rows prevented users from renewing or stacking plans across multiple duration increments.

---

## The Code / Diff

### 1. Decoupled Pub/Sub Worker Dispatch & Ephemeral Storage

We isolated generation requests into Google Cloud Pub/Sub events, handled by decoupled subscriber pods with automatic scratch directory isolation:

```python
# contentgen-services/app/entrypoints/video_worker.py:43-104
@asynccontextmanager
async def isolated_scratch_dir(job_id: str):
    scratch_path = Path(f"/tmp/workers/jobs/{job_id}")
    scratch_path.mkdir(parents=True, exist_ok=True)
    try:
        yield scratch_path
    finally:
        shutil.rmtree(scratch_path, ignore_errors=True)

async def handle_video_message(message):
    payload = json.loads(message.data.decode("utf-8"))
    job_id = payload["job_id"]
    
    async with isolated_scratch_dir(job_id) as temp_dir:
        video_file = await compose_slides_ffmpeg(temp_dir, payload["slides"])
        await upload_to_storage(video_file, f"videos/{job_id}.mp4")
        await update_job_status(job_id, "completed")
        message.ack()
```

### 2. Relational Clean Separation of Features and Plans

We separated features (functional toggles) from plans (commercial products):

```python
# backend/app/domain/models/plan.py
class Feature(Base):
    __tablename__ = "features"
    code: Mapped[str] = mapped_column(String(64), unique=True, primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    feature_code: Mapped[str] = mapped_column(ForeignKey("features.code"))
    duration_days: Mapped[int] = mapped_column(Integer) # 30 or 365
    price_cents: Mapped[int] = mapped_column(Integer)
```

---

## Notes & Edge Cases

- **Pub/Sub Ack Deadlines**: Long FFmpeg rendering tasks can exceed default 10-second ack deadlines; worker loops must call `message.modify_ack_deadline(60)` periodically during encoding loops.
- **Disk Saturation**: Always wrap temp directories with `try/finally` blocks to prevent unlinked temporary `.mp4` chunks from filling up ephemeral pod storage.
- **Frontend Streaming**: Use native HTML5 `<video>` tags with HLS.js instead of monolithic wrapper libraries to avoid Vite ESM bundling conflicts.
