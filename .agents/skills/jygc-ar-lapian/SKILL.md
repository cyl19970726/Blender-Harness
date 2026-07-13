---
name: jygc-ar-lapian
description: Use for project-specific AR reference breakdowns, frame analysis, and storing lapian cards for Jieyang Gucheng mini program XR decisions.
---

# JYGC AR Lapian

## Purpose

Turn AR reference videos, screenshots, and product examples into decisions usable by the Jieyang Gucheng mini program XR route.

## Storage

- Accepted reference cards go to `docs/reference/ar-library/`; read that directory's README and, when present, its index first.
- Raw frames, downloads, transcripts, and extraction outputs go to gitignored `.artifacts/research/lapian/`, never directly into the card library.
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
- Classify each card against the current Target Brief and the relevant `jygc-spot-animation` or `jygc-magnet-animation` domain contract. Do not infer current priority from an old issue number.
- Scenic-spot and magnet/card routes are independent options; their active, paused, or rejected status must come from current product evidence, not this skill.
- A reference that depends on runtime camera movement is not implementation proof for a fixed-camera scenic effect layer, though it may remain art-direction evidence.
- Historical rejected routes remain negative evidence only within their recorded scope; a later owner decision may reopen them.

## Storage note

`docs/reference/ar-library/` is the canonical accepted-card location in this Harness repository. The library is intentionally lightweight; source media remains external or under `.artifacts`, with stable source URL, capture date, provenance, and any local SHA256 recorded in the card.
