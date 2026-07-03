---
name: jygc-ar-assets
description: Use for organizing, classifying, moving, packaging, or publishing Jieyang Gucheng AR assets across the repo, mini program package, CDN, or CloudBase Storage.
---

# JYGC AR Assets

## Source of truth

Read and update `docs/reference/ar-assets/manifest.json` before changing AR asset paths. Once `docs/ASSET_LAYOUT.md` lands (asset layout for the Blender pre-render pipeline, issue #130/#131/#133), read it first for the current on-disk structure of trigger images / source .blend / render outputs / harness candidate directories; this skill's manifest workflow still governs status/classification.

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
- Content-mainline outputs are pre-rendered video (加法光黑底 for 景点合同 / SBS alpha for 卡面合同), not standalone GLB character models; do not default new scenic-spot or magnet asset entries to a GLB-avatar shape unless the item is explicitly an XR-Frame prop/UI asset.

## Reorg sequence

1. Mark the asset group and status in manifest.
2. Decide runtime location: mini program package, CloudBase Storage, CDN, or archive.
3. Update code paths and preload/fallback behavior.
4. Run package-size and true-device checks.
5. Attach evidence to the relevant CSDC item.
