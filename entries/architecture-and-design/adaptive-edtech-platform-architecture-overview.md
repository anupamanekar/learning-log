---
id: "adaptive-edtech-platform-architecture-overview"
title: "Adaptive EdTech Platform: Event-Driven Multimedia Workers, Ephemeral Disk Isolation, and Entitlement Modeling"
project: "adaptive-edtech-platform"
date: "2026-11-21"
category: "architecture-and-design"
tags: ["adaptive-edtech-platform", "architecture", "pubsub", "fastapi", "workers", "ffmpeg", "firestore", "vite"]
severity_or_impact: "Critical"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "contentgen-services/app/services/pubsub_client.py:67-133"
  - "contentgen-services/app/entrypoints/video_worker.py:43-104"
  - "backend/app/adapters/api/payments.py:57-90"
  - "frontend/src/components/common/VideoPlayer.tsx:22-40"
  - "documentation/architecture/ARCHITECTURE_REVIEW_LOAD_LIMITS.md:7-45"
---

# Adaptive EdTech Platform: Event-Driven Multimedia Workers, Ephemeral Disk Isolation, and Entitlement Modeling

## Problem
The Adaptive EdTech Platform automatically synthesizes personalized, localized lesson modules combining slide rendering (Pillow), text-to-speech audio synthesis (Sarvam AI), and final video composition (FFmpeg). As user adoption grew, the platform encountered three systemic architecture failures:
1. **Web Server Process Crashes (OOM)**: Running FFmpeg subprocesses directly inside background threads of the FastAPI container consumed all available RAM, causing Linux kernel OOM kills (`SIGKILL 137`) that dropped active student connections.
2. **Entitlement vs Duration Conflation**: An early data model conflated application functional privileges (e.g. `creator_studio`, `ai_tutor`) with commercial billing tiers, breaking renewal calculations and preventing cumulative subscription stacking.
3. **Bundler Breakage with Third-Party Players**: Using CommonJS video players (`react-player`) triggered build-time hydration mismatches and Vite ESM rollup bundle breakages on production deployments.

## Root Cause
- **Lack of Process Boundaries**: CPU/memory-intensive rendering jobs competed with I/O-bound HTTP request handling inside the same operating system container.
- **Relational Domain Modeling Failure**: Treating feature capabilities and commercial plans as interchangeable attributes on a single table rather than establishing an M:N link between static features and time-bounded commercial plans.
- **Legacy CJS Video Library Dependencies**: Incomplete ESM compliance in popular legacy React video packages caused broken dynamic imports in modern Vite/Rollup pipelines.

## Solution & Code

### 1. Decoupled Pub/Sub Worker Topology & Ephemeral Disk Cleanup
We extracted video compilation and audio synthesis into standalone worker pods that ingest tasks from Google Cloud Pub/Sub via `StreamingPull`. Each worker creates a dedicated ephemeral scratch directory bounded by strict cleanup guarantees:

```python
# contentgen-services/app/entrypoints/video_worker.py:43-104
@asynccontextmanager
async def isolated_scratch_dir(job_id: str):
    scratch_path = Path(f"/tmp/workers/jobs/{job_id}")
    scratch_path.mkdir(parents=True, exist_ok=True)
    try:
        yield scratch_path
    finally:
        if scratch_path.exists():
            shutil.rmtree(scratch_path, ignore_errors=True)

async def process_video_job(message: pubsub_v1.subscriber.message.Message):
    data = json.loads(message.data.decode("utf-8"))
    job_id = data["job_id"]
    
    async with isolated_scratch_dir(job_id) as temp_dir:
        output_mp4 = await render_ffmpeg_slides(temp_dir, data["slides"])
        await upload_to_gcs(output_mp4, destination=f"lessons/{job_id}.mp4")
        await firestore_db.collection("jobs").document(job_id).update({"status": "completed"})
        message.ack()
```

### 2. Relational Boundary: Features vs Plans
We refactored database tables to cleanly decouple static capability flags (`features`) from commercial purchases (`plans`), implementing cumulative expiry stacking inside `user_plans`:

```python
# backend/app/domain/models/plan.py
class Feature(Base):
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    feature_code: Mapped[str] = mapped_column(ForeignKey("features.code"))
    duration_days: Mapped[int] = mapped_column(Integer) # e.g. 30 or 365
    price_cents: Mapped[int] = mapped_column(Integer)

class UserPlan(Base):
    __tablename__ = "user_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

### 3. Native Vite ESM Video Player
We replaced external npm dependencies with a native HTML5 video component with HLS.js lazy loading, eliminating ESM build breakages and trimming client bundle size by 42KB.

## Key Takeaway
- Decoupling media synthesis into dedicated, ephemeral worker pods guarantees that peak rendering loads never destabilize core HTTP APIs.
- Features represent permanent code capabilities; plans represent time-bounded commercial contracts. Decoupling them is mandatory for sane subscription renewals.
- Native browser primitives (HTML5 `<video>`) outperform heavy CJS wrapper packages in modern Vite ESM environments.
