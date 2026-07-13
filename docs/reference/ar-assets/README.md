---
status: historical-cross-repo-snapshot
carrier: imported-product-docs
owner: longling
last-reviewed: 2026-06-25
related:
  - "docs/audit/ar-knowledge-inventory-2026-06-25.md (git @03940cf8)"
---

# AR Asset Manifest

> 本目录是从产品仓迁移时保留的 2026-07 快照。它引用的 `_assets-src`、`wechat-*`、PRD、ADR 和迁移计划并不位于当前独立 Harness 仓；路径或状态只有在产品仓重新核验后才可执行。

`manifest.json` 是历史 AR 资产处置状态的索引。它不替代素材源文件，也不代表文件仍存在、已经完成小程序迁移或仍是当前主线。

冰箱贴逐项盘点见 [`fridge-magnets.md`](fridge-magnets.md)。12 景点 AR 触发图的历史覆盖与缺口见 [`spot-trigger-images.md`](spot-trigger-images.md)。旧执行计划只能从原产品仓历史 `@03940cf8` 恢复，不在本仓伪造替代文件。

状态含义:

- `active`: 已经在小程序产品中使用。
- `active-candidate`: 进入小程序 XR 主线验证的候选资产。
- `archive-candidate`: 有历史或素材价值,但需要重判是否进入新主线。
- `evidence-only`: 只作为验证过程或失败探索证据。
- `deprecated`: 技术路线退役,不得作为新实现依赖。
- `rejected`: 产品方向否决,只保留溯源。

变更规则:

1. 在产品工作区新增、移动、删除或替换 AR 资产前，先找到并更新其当前 live manifest；不要直接把本快照改成当前状态。
2. 进入小程序运行路径前必须明确 `runtimeTarget` 和包体/CDN/CloudBase Storage 方案。
3. H5 AR 和 MindAR 文件不得被标记为小程序主线资产。
4. 南浦视频贴卡只能保留为 `rejected` 或 `evidence-only`。
5. 任何 `active-candidate` 升级都必须引用当前产品决策与真机验收证据；本仓缺失的旧 ADR 不能充当批准。
