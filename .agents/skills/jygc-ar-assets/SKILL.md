---
name: jygc-ar-assets
description: Use for organizing, classifying, moving, packaging, or publishing Jieyang Gucheng AR assets across the repo, mini program package, CDN, or CloudBase Storage.
---

# JYGC AR Assets

## Source of truth

Read `docs/architecture/ASSET_LAYOUT.md` before changing AR asset paths. This standalone Harness repository does not contain the product repo's `_assets-src` or `wechat-*` trees. `docs/reference/ar-assets/manifest.json` is a dated cross-repo snapshot, not proof that those paths exist here. Perform physical moves only in the product workspace after resolving its current manifest and runtime references.

## Status model

- `active`: already used by the mini program product.
- `active-candidate`: selected for mini program XR validation.
- `archive-candidate`: may be useful but is not on the current mainline.
- `evidence-only`: keep only for proof or audit history.
- `deprecated`: retired technical route.
- `rejected`: product route denied.

## Rules

- Do not create global symlinks for project assets in this phase.
- In the product repository, update its live manifest in the same change that moves or reclassifies an AR asset. Do not rewrite this historical snapshot as if it were live state.
- Do not import H5/MindAR-only assets into the mini program as product runtime assets.
- Keep package-size impact visible when moving assets into `wechat-gucheng/miniprogram/assets`.
- Prefer CDN or CloudBase Storage for large models, video, or audio once the runtime loader is defined.
- Keep Jie Xiaoxian and stamp assets aligned with the existing mini program asset family.
- Current content defaults often use pre-rendered video (加法光、SBS alpha or another reviewed composite), but the current Target Brief and probe evidence choose the output route. Do not force every scenic or magnet item into GLB or video solely because an old route used it.

## Reorg sequence

1. Enter the real product workspace and resolve its current live manifest.
2. Mark the asset group and status in that manifest.
3. Decide runtime location: mini program package, CloudBase Storage, CDN, or archive.
4. Update code paths and preload/fallback behavior.
5. Run package-size and true-device checks.
6. Attach the immutable evidence/manifest reference to the relevant project record.
