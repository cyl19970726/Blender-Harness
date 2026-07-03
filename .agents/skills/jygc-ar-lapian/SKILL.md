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

- Prefer examples that can become a true-device WeChat mini program VisionKit + XR-Frame implementation.
- Treat H5-only examples as visual references, not implementation proof.
- Classify each card against the two live output contracts (see issue #135 §0): 卡面合同(磁贴/印章卡,微缩世界+虚拟运镜+扑镜,天坛/长安/中央大街 as quality bar)or 景点合同(扫真楼,固定机位效果层,无运镜,加法光+SBS alpha)。A reference that only works with runtime camera movement is not directly reusable for 景点合同。
- Both scenic-spot (currently Jinxianmen, issue #136) and fridge-magnet/card production are active mainlines; do not treat one as subordinate to the other.
- Nanpu video-card references are negative evidence unless a later ADR reopens that route.

## Storage note

The live card library at `docs/reference/ar-library/` (with `index.md`, `external/`, `internal/`) already implements this skill's card schema and is the canonical location — read `docs/reference/ar-library/README.md` for the current card schema and index before adding a new card.
