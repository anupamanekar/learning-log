---
id: "vite-esm-react-player-breakage"
title: "Why react-player Broke in Vite and How Native Embeds Solved It"
project: "ai-directed-learning"
date: "2026-02-08"
category: "mistakes-and-pitfalls"
tags: ["react", "vite", "bundling", "esm", "video-player", "frontend"]
severity_or_impact: "High"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "ai-directed-learning/documentation/VIDEO_PLAYER_FIX_COMPLETE.md"
  - "ai-directed-learning/frontend/src/components/VideoPlayer.tsx"
---

# Why react-player Broke in Vite and How Native Embeds Solved It

## 🔍 Context & Scenario
In the **ai-directed-learning** platform, students access multimedia lessons containing video content hosted on YouTube, Vimeo, or served as direct MP4 files. The team originally integrated `react-player` (v3.4.0) to handle universal video rendering.

## 💥 The Incident & Symptoms
- Students reported that videos rendered blank or failed to load entirely.
- The player DOM node was generated, but instead of rendering a YouTube `<iframe>`, it unexpectedly rendered an empty HTML5 `<video>` tag.
- Calling `ReactPlayer.canPlay(url)` returned `true`, but the player component silently misclassified the URL or failed to mount the iframe.
- Attempting to downgrade from `react-player` v3.4.0 to v2.16.0 did **not** resolve the issue.

```
Expected: <iframe src="https://www.youtube.com/embed/xyz" ... />
Actual:   <video class="react-player" ...></video> (unplayable, black box)
```

## 🛠️ Root Cause Analysis
1. **ESM vs CJS Bundling with Vite**: Modern Vite uses ES module rollups in production and esbuild in dev. `react-player`'s internal dynamic import pattern for platform-specific sub-players (YouTube, Vimeo, SoundCloud) failed to resolve properly in Vite's ESM bundling pipeline.
2. **Fallback to HTML5 Tag**: When sub-player loaders fail to resolve, `react-player` falls back to its generic FilePlayer, which creates a `<video>` tag. The YouTube URL was passed to `<video src="...">`, which browsers cannot decode.

## 💡 The Solution: Native Embed Component
Instead of fighting third-party bundle wrappers, we replaced the library with a custom, zero-dependency `VideoPlayer` component supporting YouTube, Vimeo, and HTML5 video via clean URL parsing.

### Implementation:
```tsx
export const VideoPlayer: React.FC<{ url: string; title?: string }> = ({ url, title }) => {
  const getEmbedUrl = (rawUrl: string): { type: 'youtube' | 'vimeo' | 'file'; embedUrl: string } => {
    // YouTube parsing
    const ytMatch = rawUrl.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
    if (ytMatch) {
      return { type: 'youtube', embedUrl: `https://www.youtube.com/embed/${ytMatch[1]}?autoplay=0&rel=0` };
    }

    // Vimeo parsing
    const vimeoMatch = rawUrl.match(/vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/(?:[^\/]*)\/videos\/|)(\d+)/);
    if (vimeoMatch) {
      return { type: 'vimeo', embedUrl: `https://player.vimeo.com/video/${vimeoMatch[1]}` };
    }

    // Direct video file fallback
    return { type: 'file', embedUrl: rawUrl };
  };

  const { type, embedUrl } = getEmbedUrl(url);

  if (type === 'youtube' || type === 'vimeo') {
    return (
      <div className="relative w-full aspect-video">
        <iframe
          src={embedUrl}
          title={title || 'Lesson Video'}
          className="w-full h-full rounded-lg"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <video controls className="w-full aspect-video rounded-lg">
      <source src={embedUrl} />
      Your browser does not support HTML5 video.
    </video>
  );
};
```

## 🎬 Showcase Angle (For Blog / Vlog)
- **Title**: *"Stop Using Heavy Video Player Libraries in Modern Vite Projects"*
- **Hook**: Showing how a 200KB bundle dependency that silently failed in production was replaced by 35 lines of native React code with better performance and zero bundle baggage.
- **Key Takeaway**: Don't import complex multi-provider libraries when native `<iframe>` and HTML5 tags with regex parsing solve 100% of your real requirements.
