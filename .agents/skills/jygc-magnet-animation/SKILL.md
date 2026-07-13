---
name: jygc-magnet-animation
description: 揭阳古城冰箱贴、印章卡和文创卡的卡面 AR 动画领域合同、路线选择与探针菜单。用于微缩世界、破框立起、虚拟运镜、擦镜/扑镜、SBS alpha、预渲染视频、磁贴 SKU 创意或判断候选是否符合卡面产品体验。它帮助选择最低成本的定帧、motion、edge-owner、A/V 或 runtime probe，不规定固定 Phase/Gate、固定帧数或评审编排。
---

# 揭阳古城卡面 AR 动画

本 skill 负责“卡面产品应当成立什么”和“当前最值得验证什么”。Harness 的 RouteHypothesis、ProbeRun、Evidence 与 RouteDecision 见 `docs/architecture/HARNESS_V1.md`；具体失败按需读 `docs/knowledge/AR_PRODUCTION_CASEBOOK.md`。

## Domain contract

- 卡面是手持平面商品，不是真实建筑。允许虚拟运镜、微缩纵深、破框、绕场、近镜擦过或扑镜，但这些都是可选视觉语法，不是固定七拍模板。
- 动画必须从这枚商品和这处景点的形状、材质或史料锚生长。把同一创意换到任意磁贴仍成立，说明专属性不足。
- 目标是最终手持观看体验，不是 Blender 裸渲染、alpha 指标或微信播放链路本身。
- 可见边缘要由真实物体、同源 pass 或经批准的 artist matte 拥有。烟雾、blur、背景色和几何 slab 不能被用来无意遮住未解决的主体。
- 会占据近镜或大面积画面的资产，质量压力最高；先证明该镜头，再投资全长。
- runtime smoke 只回答 tracking、播放、shader、重播和性能，不批准创意、模型或动画。
- 有 A/V 目标时，声音 cue 必须在动态证据里对应可见动作；静帧不能批准 motion/audio。

参考视频用于目标语法和质量比较，不是要求逐拍复制。现有旧简版招手 hero 只作历史资产，不作为质量基线。

## Route options

根据目标画面、预算、是否需要透明边缘和是否需要视角变化选择，不必顺序尝试。

### A. Blender/CG beauty + same-source matte

适合需要可靠透视、真实虚拟运镜、连续遮挡和精确 owner 的微缩世界。Blender 同源输出 beauty 与 matte/source pass，再打包为 runtime 媒体。

### B. 2.5D layered artwork

适合已有高质量定帧、运动主要是展开、视差、局部活化或轻度镜头变化。AI/插画可作为元素和纹理来源；最终层、边缘和文字要可控。

### C. Generated motion + authored extraction

适合生成视频能提供难以手工制作的质感或运动，但必须先证明可以得到稳定、真实的可见边缘。若只能从 flattened MP4 猜主体，先做 extraction probe，失败即改路。

### D. Lightweight realtime 3D

仅在绕看、交互或实时视差确实创造产品价值，且包体/性能/材质能满足目标时采用。不要因为“已有 GLB”就默认走实时 3D。

### E. Hybrid

允许预渲染主体、透明媒体、少量实时粒子/UI/角色层组合。先定义每层的 owner、合成模式和失败边界。

## Probe menu

| 当前未知 | 最便宜的探针 | 需要看到 | 改路信号 |
| --- | --- | --- | --- |
| 创意是否专属于这枚磁贴 | target-frame probe | 1–3 张真机模拟帧；商品边缘、景点锚、高潮和纪念态 | 换景仍成立；主角与商品无关系；只剩通用炫技 |
| 微缩/破框空间是否成立 | depth probe | 短 animatic 或低成本 playblast；前后景、卡面边缘和相机关系 | 只像平面视频；虚拟相机没有增加空间价值 |
| 主体能否承受峰值镜头 | peak-coverage probe | 目标分辨率下最丑/最近/覆盖最大的帧和相邻时间证据 | 低模、proxy、材质糊、只靠 motion blur 遮丑 |
| 边缘是否属于物体 | edge-ownership probe | beauty、matte、composite 并排；关键对象逐帧 owner | 竖向视频窗、slab、背景/店铺/天空误入 alpha |
| 动画是否有意图 | motion probe | main view 加必要的 top/side/asset-only 小段；速度和遮挡可读 | 只有缩放/平移；路径物体；满屏 blob 无叙事动机 |
| A/V 是否咬合 | cue probe | 带声短片；关键 cue 时间与动作点 | “空手倒茶”、音效空响、单帧无法证明节奏 |
| runtime 路线是否可用 | runtime smoke | tracking、视频/GLB、alpha、replay、性能 | 技术失败；注意技术通过不改变视觉结论 |
| 全长投资是否值得 | cost probe | 最风险的 2–5 秒达到目标，且路线预算/stop condition 清楚 | 关键段仍不成立；继续只增加版本、不增加信息 |

定帧赛马是昂贵创意的可选方法，不是强制编排。候选数、是否并行、评审角色和是否杂交由当前项目决定。简单且可逆的修改不必先组织 tournament。

## Product review questions

评审者根据 Target Brief 和证据回答：

1. 第一眼是否仍认得商品、景点和主要物体？
2. 最接近镜头、最难看的时刻是否仍像成品？
3. 破框、绕场或扑镜是否服务叙事，而不是遮丑？
4. 边缘与透明关系在真实相机上是否可信？
5. 这条路线下一步最昂贵的未知是什么？

局部 probe 只能得到 `continue/revise/abandon/ask_owner` 的路线建议。不要把某个 alpha、rig 或 runtime proof 命名为整片 accepted。

## Project content

- 每枚磁贴从该景内容卡和史料来源派生；未经核实的诗句、楹联、人物或年份不得进入产品。
- 纪念态、印章纹样和“下一站”钩子可用于连接集章/复游玩法，具体是否采用由产品 brief 决定。
- 潮州音乐、童声或特定 motif 是项目美术选项，不是 harness 核心常量。

## Pointers

- 重资产与发布媒体位置：`docs/architecture/ASSET_LAYOUT.md`。
- 龙作为高风险可见资产时：`.agents/skills/jygc-dragon-rig-pipeline/SKILL.md`。
- 历史上的 proxy 盖屏、竖向视频窗、单图接 runtime、alpha owner 与 A/V 脱节：`docs/knowledge/AR_PRODUCTION_CASEBOOK.md` 的 `BH-001`、`MAG-001`、`MAG-002`、`MAG-003`、`AUDIO-001`。
