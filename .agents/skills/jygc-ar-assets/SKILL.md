---
name: jygc-ar-assets
description: Use for organizing, classifying, moving, packaging, or publishing Jieyang Gucheng AR assets across the repo, mini program package, CDN, or CloudBase Storage.
---

# JYGC AR Assets

## Source of truth

Read `docs/architecture/ASSET_LAYOUT.md` and `docs/reference/ar-assets/manifest.json` before changing AR asset paths. The layout document governs physical location; the manifest governs status/classification.

## Status model

- `active`: already used by the mini program product.
- `active-candidate`: selected for mini program XR validation.
- `archive-candidate`: may be useful but is not on the current mainline.
- `evidence-only`: keep only for proof or audit history.
- `deprecated`: retired technical route.
- `rejected`: product route denied.

## Rules

- Do not create global symlinks for project assets in this phase.
- Do not move or delete large AR files without a manifest update in the same change.
- Do not import H5/MindAR-only assets into the mini program as product runtime assets.
- Keep package-size impact visible when moving assets into `wechat-gucheng/miniprogram/assets`.
- Prefer CDN or CloudBase Storage for large models, video, or audio once the runtime loader is defined.
- Keep Jie Xiaoxian and stamp assets aligned with the existing mini program asset family.
- Current content defaults often use pre-rendered video (加法光、SBS alpha or another reviewed composite), but the current Target Brief and probe evidence choose the output route. Do not force every scenic or magnet item into GLB or video solely because an old route used it.

## Reorg sequence

1. Mark the asset group and status in manifest.
2. Decide runtime location: mini program package, CloudBase Storage, CDN, or archive.
3. Update code paths and preload/fallback behavior.
4. Run package-size and true-device checks.
5. Attach the immutable evidence/manifest reference to the relevant project record.
