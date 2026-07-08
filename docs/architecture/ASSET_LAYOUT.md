---
status: deliverable
carrier: repo-docs
owner: longling
last-reviewed: 2026-07-08
related:
  - docs/reference/ar-assets/manifest.json
  - docs/reference/ar-assets/README.md
  - .agents/skills/jygc-ar-assets/SKILL.md
  - issue #130 (磁贴生产章程)
  - issue #131 (Blender harness 作业环境)
  - issue #135 (八景总纲)
  - PR #134 (tools/blender-harness, feat/blender-harness-foundation, 未合并)
---

# 资产目录宪法(ASSET_LAYOUT)

本文档是"一个 AR 资产该放在哪个目录、用什么规则治理"的唯一权威表。它不重复
`.agents/skills/jygc-ar-assets/SKILL.md` 已讲清的 manifest 状态模型/操作序列——
那本 skill 管"怎么改",本文档管"改到哪"。两者冲突时以 manifest 状态定义为准，
以本文档的路径归属为准。

## 0. 现状扫描(写这份宪法前核过的事实)

- `_assets-src/<asset-id>/` + `PROVENANCE.md` 已有实践范式:主工作区
  `_assets-src/jiexiaoxian/PROVENANCE.md`(揭小贤 3D 源资产台账)。本文档把这个
  范式确立为**所有 IP/角色源资产的强制格式**，不是揭小贤专属。
- `docs/reference/ar-assets/manifest.json`(schema `jygc.ar-assets.v1`)是现役总登记，
  已有 `active` / `active-candidate` / `archive-candidate` / `evidence-only` /
  `deprecated` / `rejected` 六态，状态定义见同目录 `README.md`，不在此重复。
- 小程序主线是 `wechat-gucheng/`。早期的 `wechat-ar/`、`wechat-jinxianmen/` 实验脚手架已于
  2026-07-08 删除(ADR 0006 判其退出主线 + 用户拍板，
  清理记录见 `docs/migration/2026-07-08-scaffold-asset-cleanup.md`(git @03940cf8)，历史入口 tag `h5-final`)，
  其中散放的触发图/marker(如已删的 `wechat-ar/miniprogram/assets/marker.jpg`)一并随脚手架退役。
  新的触发图与 marker 一律落 `wechat-gucheng` 的 `markers/<spot>-marker.jpg` 子目录——
  本文档把这个子目录结构定为新资产的强制去向。
- `tools/blender-harness/fixtures/`（PR #134，分支 `feat/blender-harness-foundation`，
  引用时须注明"尚未合并"）已有金反例范式：`gate-d-v01-negative/`、
  `synthetic-accepted-control/`。
- `.gitignore` 已声明 `.artifacts/` 整体 gitignored——本文档确认这是全量渲染产物的
  唯一合法落点，不要另开根目录。
- 原重资产研究目录 docs/research/ 已随 docs 架构 v2(ADR 0007,2026-07-08)整体删除,恢复入口 git 历史 @03940cf8;
  研究草稿不再入库。参考语法/拉片的权威落点改为 `docs/reference/ar-library/`(已有拉片卡范式);
  轻量判读证据(gate boards/review JSON)的新落点未定,见 ADR 0007 未决事项。

## 1. 资产类与位置

| 资产类 | 位置 | 规则 |
|---|---|---|
| 触发图源片(实拍原片+机位记录) | `_assets-src/triggers/<spot>/` + `PROVENANCE.md` | 记拍摄日期/时段/机位/EXIF；三类图分开铁律（参考图/触发图/动画美术图不得混放同目录） |
| 生产 marker(压缩版) | `wechat-gucheng/miniprogram/ar/assets/markers/<spot>-marker.jpg` | 小程序 AR 页面代码引用的唯一压缩版；新增/替换必须同一改动内登记 manifest |
| IP/角色源资产(三视图/高模/绑骨源) | `_assets-src/<asset-id>/` + `PROVENANCE.md` | 大二进制（>5MB）不进 git → 外部归档 + manifest 记 SHA256；`PROVENANCE.md` 格式见 §2 |
| runtime GLB/短音频 | `wechat-*/miniprogram/**/assets/` | GLB ≤ 2MB（XR-Frame 包体红线，见 xr-frame skill）；进包前必过压缩流程 |
| 发布视频(SBS/加法层) | CloudBase 云存储 | 超出小程序 2MB 主包限制的一律走 CloudBase；manifest 登记 URL + SHA256 |
| 全量渲染产物 | `.artifacts/blender-harness/<candidate-id>/` | gitignored（`.gitignore` 已声明 `.artifacts/`），任意大，不受体积约束 |
| 轻量判读证据(boards/audit/review) | 落点待定(原 docs/research/ 已删,git 历史 @03940cf8 可查) | 全量渲染仍在 `.artifacts/`;评审板/JSON 的入库落点由后续 ADR 定夺(见 ADR 0007 未决事项),定夺前不归档进 git |
| 参考语法/拉片 | `docs/reference/ar-library/` | 外部对标视频逐帧拆解、语法沉淀的唯一落点(接替 #133 原定的 research 路径,该目录已随 docs 架构 v2 删除) |
| 金反例 | `tools/blender-harness/fixtures/` | PR #134（未合并，分支 `feat/blender-harness-foundation`）；每个金反例一个子目录 + `README.md` 说明"为什么必须永远被拒" |
| 音频源(TTS 工程/音乐工程/采样) | `_assets-src/audio/<spot\|sku>/` | 声线锁 `zh-CN-YunxiaNeural`（童声）；音源版权/授权来源必须记录在同目录 `PROVENANCE.md` |
| 总登记 | `docs/reference/ar-assets/manifest.json` | **登记才算存在**；状态枚举见 `docs/reference/ar-assets/README.md`（`active` / `active-candidate` / `archive-candidate` / `evidence-only` / `deprecated` / `rejected`） |

## 2. `PROVENANCE.md` 必写字段

任何 `_assets-src/<asset-id>/` 目录必须有 `PROVENANCE.md`，至少覆盖（范式见
`_assets-src/jiexiaoxian/PROVENANCE.md`）：

1. 目录结构说明（子目录 → 是什么）。
2. **保留集**表：文件 / 是什么 / 格式 / 备注——只列权威源，不列中间产物。
3. **派生链**：源 → 处理步骤 → 现役产物的完整箭头链；派生链不确证时明确写"重建，非 100% 确证"，不得假装确定。
4. 格式真相：文件扩展名与真实格式不符时必须记录（历史教训：多个 `.glb` 实为 FBX，靠 `file` 命令验证后改回真扩展名）。
5. 待办/未决：未定位、未统一的资产明写，不得略去装作已解决。

触发图源片的 `PROVENANCE.md` 额外必写：拍摄日期、时段（早/午/晚/夜）、机位（坐标或
文字描述+参考照片）、EXIF（焦距/朝向）。这是配准工艺（fSpy/photo-match）的输入，缺一项
下游建筑代理白模就对不齐。

音频源的 `PROVENANCE.md` 额外必写：TTS 工程用的声线 ID 与参数、音乐工程的授权/采样来源、
若为真人配音须写配音者与授权范围。

## 3. 铁律

1. **权威素材不进 `/tmp`**。macOS 会清 `/private/tmp`，历史上已丢过定帧并连累 workflow
   跑挂。任何要长期存在的素材必须落 repo（`_assets-src/`、CloudBase）
   或明确登记在 manifest 里的外部归档，不允许"先放 tmp 以后再说"。
2. **三类图严格分开**：参考图（外部对标，不进产品）/ 触发图（实拍锚点，AR 识别用）/
   动画美术图（overlay，渲染产物）三者物理目录不得混放。混放会导致下游误把参考图当触发图
   用，或误把触发图当美术素材改动。
3. **PROVENANCE 必写**，见 §2。没有 `PROVENANCE.md` 的 `_assets-src/<asset-id>/` 视为
   未完成登记，不得被下游引用为权威源。
4. **manifest 登记 = 存在的唯一凭证**。任何 AR 资产（触发图、marker、GLB、音频、发布视频）
   在被下游代码或流程引用之前，必须先在 `docs/reference/ar-assets/manifest.json` 登记
   `id` / `category` / `paths` / `status` / `runtimeTarget`。**Untracked = 不存在**——
   金反例：曾有 461MB 素材全程 untracked，未登记也未提交，事故发生前无人知道它存在过。
5. **大二进制策略**：
   - `.artifacts/blender-harness/` 下的全量渲染产物：gitignored，任意大，不进 git。
   - `_assets-src/` 下 >5MB 的源文件：不进 git，走外部归档（对象存储/Drive），
     manifest 或 `PROVENANCE.md` 记 SHA256 用于校验一致性。
   - `wechat-*/miniprogram/**/assets/` 下的 runtime 资产：受包体红线约束
     （GLB ≤ 2MB），不是"大二进制随便放"的例外。
   - CloudBase 云存储：超出小程序主包限制的发布视频/大音频的唯一合法落点，manifest
     必须记 URL + SHA256（没有 SHA256 无法验证云端文件与本地源一致）。
6. **pass owner 溯源用机检，不用手写声明**。资产 ID 的 pass owner 应由 `.blend` 文件
   实际遍历推导，不能靠人工写的溯源声明——历史教训：手写 acceptance 声明会说谎。
   适用于任何跨目录的资产溯源核对。
7. **状态枚举与变更规则**不在本文档重复定义，见
   `docs/reference/ar-assets/README.md` 与 `.agents/skills/jygc-ar-assets/SKILL.md`；
   本文档只管物理位置，状态语义以那两份为准。

## 4. 与现状的冲突点（写作时发现，未强制立即批量迁移）

- **marker 子目录尚未落地**：历史上 marker 文件曾直接散放在实验脚手架
  `miniprogram/assets/` 根下（如已删的 `wechat-ar/miniprogram/assets/marker.jpg`、
  `wechat-jinxianmen/miniprogram/assets/marker.jpg`），没有按
  `ar/assets/markers/<spot>-marker.jpg` 的子目录+命名规则组织。这两个脚手架已于 2026-07-08
  删除（历史入口 tag `h5-final`，清理记录见 git 历史 @03940cf8 `docs/migration/2026-07-08-scaffold-asset-cleanup.md`），
  存量 marker 随之退役。本文档把该路径结构定为 `wechat-gucheng` 主线里**新资产的强制去向**；
  进贤门线在主程序内重做时按此规则命名新 marker，不倒查补齐已删的旧文件。
- **触发图源片目录尚未建立**：仓库目前没有 `_assets-src/triggers/<spot>/` 目录，
  触发图相关的源片/机位记录目前分散在各小程序 `assets/` 或未系统留档。本文档确立
  该路径为唯一权威去向，下一个新触发图产出即应遵循，不倒查补齐旧触发图。
- **参考语法/拉片落点已改**：#133 原定的 reference-grammar 路径在 docs/research/ 下(已删,git 历史 @03940cf8 找回),
  该目录已随 docs 架构 v2 整体删除。新的参考语法/拉片沉淀一律落
  `docs/reference/ar-library/`(§1 表),不再建 research 目录。
- **`_assets-src/audio/` 尚未建立**：现有音频（narration.mp3 等）目前在
  `public/ar/magnets/<spot>/` 下随磁贴资产混放，manifest 中以 `legacy-fridge-magnet-ar`
  类别登记，还没有独立的 `_assets-src/audio/<spot|sku>/` 源工程目录。本文档确立后者为
  TTS 工程/音乐工程的权威源目录（区别于 runtime 短音频，见 §1 表）；新音频源产出走此路径。
- **`tools/blender-harness/` 尚未合入本 worktree 所在分支**：PR #134 仍在
  `feat/blender-harness-foundation` 分支（独立 worktree
  `jieyanggucheng-blender-harness`），本 skills 分支（`feat/ar-skills-reorg`）尚未
  合并该改动。引用金反例路径时必须注明"PR #134，尚未合并"，不得暗示已在主分支可用。
