---
status: deliverable
carrier: repo-docs
owner: longling
last-reviewed: 2026-07-13
related:
  - docs/reference/ar-assets/manifest.json
  - docs/reference/ar-assets/README.md
  - .agents/skills/jygc-ar-assets/SKILL.md
  - docs/architecture/HARNESS_V1.md
---

# 资产目录边界

本文只回答“资产放哪里”；Blender 作业语义以 `HARNESS_V1.md` 为准。`_assets-src`、`wechat-*` 和 CloudBase/CDN 路径属于揭阳古城产品工作区，本独立 Harness 仓不要求它们存在。`docs/reference/ar-assets/manifest.json` 是迁移时保留的跨仓历史快照，不能代替产品仓的当前 manifest 或文件检查。

涉及物理移动、打包或发布时，Agent 必须先进入真实产品工作区并解析其当前 runtime 引用；不要在本仓创建空目录来伪装资产已经迁移。本文不再引用旧 `tools/blender-harness`、历史 worktree 或固定 gate。

## 位置

| 资产类 | 位置 | 规则 |
| --- | --- | --- |
| 触发图权威源片 | `_assets-src/triggers/<spot>/` + `PROVENANCE.md` | 记录拍摄日期、时段、机位和 EXIF；参考图、触发图、美术图分开 |
| 生产 marker | `wechat-gucheng/miniprogram/ar/assets/markers/<spot>-marker.jpg` | 新增或替换时同步更新 manifest 和 runtime 引用 |
| IP/角色/道具权威源 | `_assets-src/<asset-id>/` + `PROVENANCE.md` | 保存 brief、来源、三视图和轻量 manifest；大文件走外部归档并记 SHA256 |
| 音频权威源 | `_assets-src/audio/<spot-or-sku>/` + `PROVENANCE.md` | 记录声线、工程、采样/音乐授权和派生链 |
| Harness 作业与失败尝试 | `.artifacts/blender-harness-v1/` | gitignored；保存 run、日志、证据和失败 attempt，不是发布目录 |
| Hunyuan 作业 | `.artifacts/hunyuan/jobs/` | JobHandle、脱敏响应、私有短期 URL、下载产物和 SHA256；不是发布目录 |
| Tripo 作业 | `.artifacts/tripo/jobs/` | JobHandle、input SHA、`0600` token/短期 URL、fetch attempts、下载产物和 SHA256；不是发布目录 |
| 路线工作区 | `.artifacts/routes/<route-group>/` | revision DAG、probe、evidence、review、decision 和 knowledge proposal |
| 小程序包内轻量 runtime 资产 | `wechat-*/miniprogram/**/assets/` | 更新前评估包体并登记 manifest；不要把大工作文件复制进包 |
| 大型发布媒体 | CloudBase / CDN / 其他已批准对象存储 | manifest 记录稳定 URL、SHA256、size、来源和回滚版本 |
| 参考拉片与可复用语法 | `docs/reference/ar-library/` | 轻量、可追溯；不作为产品触发图或最终素材 |
| 具体失败经验 | `docs/knowledge/AR_PRODUCTION_CASEBOOK.md` | 保存 scope/evidence/lesson/scope limit，不编译成通用 gate |

## `PROVENANCE.md` 最小字段

1. 目录和保留集说明；
2. 来源、授权与取得日期；
3. 权威源 → 处理步骤 → 当前产物的派生链；
4. 文件真实格式、SHA256 和外部归档位置；
5. 尚未确认的事实，明确写“未知”而不是补猜。

触发图额外记录机位/EXIF；音频额外记录声线、配音者或采样授权；生成式资产额外记录 provider、operation、JobHandle 和输入 hash。

## 不变量

- 权威源不能只存在于 `/tmp`、聊天附件或短期签名 URL。
- `_assets-src` 中的权威资产必须有 provenance；runtime 引用必须在 manifest 登记。
- `.artifacts` 是作业和证据区，不因某个 run 成功就自动成为产品源。
- 参考图、识别触发图和动画美术图不得混放或互相冒充。
- 大二进制不默认进入 Git；选择对象存储、Drive、Release 或其他归档后记录 SHA256 和回滚版本。
- pass/source owner 应从真实场景和产物推导，不能只信生产者手写声明。

具体包体数字、CloudBase 是否唯一、GLB 是否适合作为当前产品输出，属于 runtime Target Brief 和发布配置，不是 Blender Harness 的永久核心常量。
