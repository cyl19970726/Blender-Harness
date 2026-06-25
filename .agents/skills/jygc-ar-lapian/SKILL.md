---
name: jygc-ar-lapian
description: Use for project-specific AR reference breakdowns, frame analysis, and storing lapian cards for Jieyang Gucheng mini program XR decisions.
---

# JYGC AR Lapian

## Purpose

Turn AR reference videos, screenshots, and product examples into decisions usable by the Jieyang Gucheng mini program XR route.

## Storage

- Polished reference cards go to `docs/reference/ar-library/`.
- Raw extraction outputs may stay in the current research tree until a dedicated lapian research folder is created.
- A card must state whether the reference is useful for WeChat mini program XR, art direction only, or rejected for this project.

## Required fields for a new card

- Source and capture date.
- Runtime assumption: native app, mini program, H5, WebAR, unknown.
- Tracking mode: marker, image target, plane/world anchor, VPS/SLAM, video overlay, unknown.
- Useful mechanics for Jieyang.
- Risks for mini program delivery.
- Decision: `reuse`, `adapt`, `art-reference-only`, or `reject`.

## Project bias

- Prefer examples that can become a true-device WeChat mini program XR implementation.
- Treat H5-only examples as visual references, not implementation proof.
- The Jinxianmen Guo Zhiqi route has priority over generic fridge-magnet AR.
- Nanpu video-card references are negative evidence unless a later ADR reopens that route.
