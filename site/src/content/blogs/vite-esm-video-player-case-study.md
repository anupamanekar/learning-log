---
title: "Dev Log: Replacing react-player with Native Embeds in Vite"
slug: "replacing-react-player-native-embeds-vite"
topic: "vite-esm-react-player-breakage"
date: "2026-02-08"
status: "Published"
tags: ["react", "vite", "bundling", "frontend", "dev-log"]
references:
  - "frontend/src/components/common/VideoPlayer.tsx:22-40"
  - "frontend/src/components/common/VideoPlayer.tsx:177-226"
  - "documentation/VIDEO_PLAYER_FIX_COMPLETE.md"
---

# Dev Log: Replacing react-player with Native Embeds in Vite

**Project**: `adaptive-edtech-platform`  
**Source Ref**: [`frontend/src/components/common/VideoPlayer.tsx`](frontend/src/components/common/VideoPlayer.tsx#L22-L226)  
**Docs**: [`documentation/VIDEO_PLAYER_FIX_COMPLETE.md`](documentation/VIDEO_PLAYER_FIX_COMPLETE.md)

---

## What Broke

Video lessons weren't playing for students. The player container mounted, but rendered a black screen.

Inspecting the DOM showed `react-player` rendering:
```html
<!-- Broken output from react-player on a YouTube URL -->
<video class="react-player" src="https://www.youtube.com/watch?v=..."></video>
```
Instead of mounting an `<iframe>`, it mounted an HTML5 `<video>` tag with a YouTube page URL as `src`. Downgrading `react-player` from `v3.4.0` to `v2.16.0` didn't fix it.

---

## Why It Broke

`react-player` relies on dynamic sub-player imports for providers (YouTube, Vimeo, etc.). Under Vite's ESM bundling, the dynamic resolution failed silently. When sub-players fail to resolve, `react-player` falls back to its generic `FilePlayer` which blindly drops the URL into a `<video>` tag. Browsers can't play YouTube URLs inside `<video>`, resulting in a silent failure with no console errors.

---

## The Fix

Replaced `react-player` with a native `VideoPlayer` component. It parses URLs via regex and renders native `<iframe>` or `<video>` elements.

### 1. Regex Extraction (`VideoPlayer.tsx:22-40`)
```typescript
// frontend/src/components/common/VideoPlayer.tsx:22-40
const getYouTubeEmbedUrl = (url: string): string | null => {
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11)
    ? `https://www.youtube.com/embed/${match[2]}`
    : null;
};

const getVimeoEmbedUrl = (url: string): string | null => {
  const regExp = /vimeo\.com\/(\d+)/;
  const match = url.match(regExp);
  return (match && match[1])
    ? `https://player.vimeo.com/video/${match[1]}`
    : null;
};
```

### 2. Render Branching (`VideoPlayer.tsx:177-226`)
```tsx
// frontend/src/components/common/VideoPlayer.tsx:177-200
const youtubeEmbedUrl = getYouTubeEmbedUrl(playbackUrl);
if (youtubeEmbedUrl) {
  return (
    <div className="video-player-container" style={{ position: 'relative', paddingTop: '56.25%' }}>
      <iframe
        src={youtubeEmbedUrl}
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 0 }}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        title={title || 'Video player'}
      />
    </div>
  );
}
```

### 3. Position Tracking without Re-render Loop (`VideoPlayer.tsx:124-126`)
Tracking playback progress using React state triggers re-renders that reset `<video>` playback state. We tracked position via `useRef`:
```typescript
// frontend/src/components/common/VideoPlayer.tsx:124-126
// Track last saved position via ref (no state -> no re-render -> no position reset)
lastSavedPositionRef.current = currentTime;
```

---

## Notes & Takeaways

- Dropped ~200KB of bundle weight with zero external dependencies.
- Silent fallbacks are dangerous: if a library falls back to an unplayable HTML tag without throwing an error, end-to-end tests won't catch it unless you assert iframe presence.
- For 95% of web apps, YouTube/Vimeo regex + native iframe beats a multi-provider wrapper.
