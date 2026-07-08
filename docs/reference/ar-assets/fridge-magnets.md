---
status: deliverable
carrier: repo-docs
owner: longling
last-reviewed: 2026-06-25
related:
  - docs/decisions/0006-mini-program-ar-mainline.md
  - docs/reference/ar-assets/manifest.json
---

# Fridge Magnet Asset Inventory

This inventory classifies the existing `public/ar/magnets/*` assets after the AR mainline decision.

The current fridge-magnet files are not mini program XR runtime assets. Their H5/MindAR targets are retired. Art, narration, and selected models may be reused only after the Jinxianmen mini program XR path proves the runtime and package/CDN strategy.

## Summary

| Slug | Approx size | Current files | Reusable | Retired or rejected | Decision |
| --- | ---: | --- | --- | --- | --- |
| `gongfucha` | 12M | `.mind`, magnet, narration, `teapot.glb` | magnet art, narration, possible teapot model | `.mind`; direct H5 route | Archive candidate; model is too large for blind package import |
| `haolao` | 888K | `.mind`, magnet, narration | magnet art, narration | `.mind`; direct H5 route | Archive candidate |
| `hongtouchuan` | 796K | `.mind`, magnet, narration | magnet art, narration | `.mind`; direct H5 route | Archive candidate |
| `jinxianmen` | 1.0M | `.mind`, magnet, narration | magnet art, narration if a magnet SKU remains | `.mind`; direct H5 route | Archive candidate; do not confuse with scenic-spot Guo Zhiqi AR |
| `nanpu-yuge` | 7.0M | `.mind`, magnet, narration, video, alpha/stage/fx | narration and selected art only after re-brief | video-card route, `.mind`, SBS/video贴卡 composition | Rejected as product route; evidence only |
| `puning-dougan` | 736K | `.mind`, magnet, narration | magnet art, narration | `.mind`; direct H5 route | Archive candidate |
| `shuangfeng-qifu` | 1.0M | `.mind`, magnet, narration | magnet art, narration | `.mind`; direct H5 route | Archive candidate |

## Reuse Rules

1. Do not import `.mind` files into the mini program.
2. Do not port the H5 `/ar/magnets/[slug]` flow as product behavior.
3. Do not copy Nanpu's video-card pattern into Jinxianmen or future magnet routes.
4. Reuse narration only after copy review, cultural review, and audio-size review.
5. Reuse GLB only after triangle/texture inspection and a package-size or CloudBase/CDN decision.
6. A future mini program magnet route must use WeChat-supported recognition/XR primitives and true-device evidence.

## Physical Reorg Proposal

Do not move files in this phase. When implementation starts, use this order:

1. Create a new runtime asset target for the selected route, likely under `wechat-gucheng/miniprogram/assets/ar/` for small files or CloudBase/CDN for larger files.
2. Copy only the selected `active-candidate` files into the runtime path.
3. Leave `public/ar/magnets/*` in place until all references are removed or marked historical.
4. Archive or delete H5/MindAR-only files in a separate PR with path-reference checks.
5. Update `manifest.json`, CSDC, and acceptance evidence in the same PR as any physical move.

## Next Review

The next product review should decide whether fridge magnets remain a near-term business line after the Jinxianmen Guo Zhiqi V1. Until then, fridge magnet assets stay `archive-candidate` or `evidence-only`, not active runtime material.
