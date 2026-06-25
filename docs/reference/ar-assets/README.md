---
status: deliverable
carrier: repo-docs
owner: longling
last-reviewed: 2026-06-25
related:
  - docs/migration/decisions/0006-mini-program-ar-mainline.md
  - docs/audit/ar-knowledge-inventory-2026-06-25.md
---

# AR Asset Manifest

`manifest.json` 是当前 AR 资产处置状态的索引。它不替代素材源文件,也不代表文件已经完成小程序迁移。

冰箱贴逐项盘点见 [`fridge-magnets.md`](fridge-magnets.md)。执行计划见 [`../../migration/plans/2026-06-25-ar-xr-skill-asset-reorg.md`](../../migration/plans/2026-06-25-ar-xr-skill-asset-reorg.md)。

状态含义:

- `active`: 已经在小程序产品中使用。
- `active-candidate`: 进入小程序 XR 主线验证的候选资产。
- `archive-candidate`: 有历史或素材价值,但需要重判是否进入新主线。
- `evidence-only`: 只作为验证过程或失败探索证据。
- `deprecated`: 技术路线退役,不得作为新实现依赖。
- `rejected`: 产品方向否决,只保留溯源。

变更规则:

1. 新增、移动、删除或替换 AR 资产前先更新 manifest。
2. 进入小程序运行路径前必须明确 `runtimeTarget` 和包体/CDN/CloudBase Storage 方案。
3. H5 AR 和 MindAR 文件不得被标记为小程序主线资产。
4. 南浦视频贴卡只能保留为 `rejected` 或 `evidence-only`。
5. 进贤门郭之奇资产必须绑定 ADR 0006 和真机验收证据后才能从 `active-candidate` 升级为 `active`。
