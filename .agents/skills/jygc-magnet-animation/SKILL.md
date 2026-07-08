---
name: jygc-magnet-animation
description: 揭阳古城冰箱贴/磁贴动画（L3 卡面合同）的生产判断与不变量。当任务涉及冰箱贴动画、磁贴动画、印章卡活过来、微缩世界、天坛式扑镜、卡面合同、Gate D、龙绕楼、扫磁贴看动画、磁贴 SKU 定帧赛马、每景磁贴创意，或要判断某个磁贴动画候选能不能过闸/过 Gate D 时使用。它是"怎么判"的层：Phase×闸/边缘合同/覆盖前置闸/绑骨/proxy 生命周期/A-V 合同/定帧赛马/来源诚实。具体资产去处见 docs/architecture/ASSET_LAYOUT.md，作业环境（感知/行动/反馈三层）见 issue #131+PR #134 的 tools/blender-harness，权威 Phase 全文见 issue #130。
---

# JYGC 磁贴动画（L3 卡面合同）

## Goal（一句话）

磁贴 = 印章的实体化商品载体（L2 扫景点打卡集章 → 兑换/购买该景磁贴）；磁贴动画 = **L3 回家层**：扫磁贴 → Blender 预渲染的微缩世界按**天坛语法**演一遍（实物先行 → 点亮 → 破框立起 → 绕场 → 扑镜满屏 → 收束纪念态），收束态浮出印章纹样并回指"下一站"贤链钩子引流回场。质量基线 = 天坛/长安/中央大街逐帧并排，**现有全部旧动画（含 6 枚简版招手 hero）不合格、不作基线**；程序化/代码生成效果判死，代码只做 runtime 合成/触发/UI/音频 cue。

## 这本 skill 管什么、不管什么

- 管：磁贴动画每个 Phase 的**判断力与不变量**（关键问题 / 硬拒 / 戒律）。
- 不管路径：资产该落哪 → `docs/architecture/ASSET_LAYOUT.md`（全量渲染 `.artifacts/blender-harness/<candidate>/`；boards/audit/review 的入库落点待定——原 docs/research 已随 docs 架构 v2 删除，见 ADR 0007 未决事项；SBS 视频走 CloudBase）。
- 不管作业环境：agent 的眼/手/闸（感知多视图·行动参数化动词·反馈 gate-status.json+check-gate-status）→ issue **#131** + PR **#134** 的 `tools/blender-harness/`（未合并，引用注明）。
- 不管章程全文：每相 Phase 的完整交付物清单与逐条硬拒 → issue **#130**（本 skill 是它的判断力提炼，冲突以 #130 + 其 2026-07-03 磁贴对齐 comment 为准）。

## 卡面合同（磁贴专属，区别于景点合同）

- 磁贴 = 手持平面物 → **允许虚拟运镜 + 扑镜满屏**（景点合同扫真楼、锁死主触发图机位、无运镜——两者共享史料锚，视觉母题**必须差异化**，同一景两产品禁用同一语法）。
- 天坛语法七拍锚：实物先行 → 点亮 → 破框立起 → 绕场 orbit → 近景擦镜 → 扑镜满屏 → 收束纪念态（收束帧 = 打卡确认帧的商品版，浮出印章纹样 + "下一站"钩子）。
- 每枚磁贴创意从**该景内容卡史料层**派生（八景史料层见 #135 comment，`[H-XX]` 挂锚铁律适用：换个景点仍成立 = FAIL）。

## Phase 表（对齐 #130 Phase 0–12：每相=关键问题/硬拒精选/历史戒律）

关键问题的定义法则：**这个阶段允许什么东西漏下去，会在下游以不可挽回的方式爆炸**（从下游最坏情况反推）。

| # | Phase | 关键问题（下游最坏反推） | 硬拒精选 | 历史戒律一句 |
|---|---|---|---|---|
| P0 | 参考语法锚 | 天坛拆到每一拍可证伪、每拍标出边缘 owner + 高覆盖帧由谁拥有，否则整片没有对标坐标 | 只说"像天坛"无逐拍拆解；无高覆盖帧解释；无 edge owner | 差距从不是单点，是每层各漏一点的复利——对标锚要下放到 P4/P6/P8 具体阶段 |
| P1 | 分镜·边缘合同 | 每个高覆盖帧必须有**故事动机的 owner**（谁铺满屏、为什么） | 无 owner 的满屏遮挡；烟雾/blur/背景色遮丑；整片读成竖向视频窗 | v01 死于 f072/f116/f117 高覆盖帧无主；**proxy 引入即声明退场闸**（配对规则） |
| P2 | 工具链·插件资格 | 插件产出能否 bake+headless 复跑，且能纳入 pass ownership | 效果不可 bake；破坏命令行渲染；许可证不清；结果无法归 pass | 零插件基线在近景质感上实证失败（Gate B 五轮+Gate D 近景被拒）；**首个 spike=台基/栏杆近景救活**（质感插件是对真死因的未测杠杆） |
| P3 | 资产生成入场 | raw GLB 真落地本地 + 导入检查才算入场（不是"job DONE/有 URL"） | 只有 URL 无本地 GLB；Hunyuan raw 未落地就宣称入场 | Hunyuan/混元只是**来源**不是 final 龙，不得跳过 Blender 扶正/retopo/UV/材质/rig/多视图/source-pass 闸 |
| P4 | 模型质感 | **资产质量 = f(峰值入镜覆盖)**：任何帧覆盖>N% 的资产建模阶段必须先过近景质量闸 | 低模球/管/capsule 当 hero；近景材质糊；台基/栏杆/植被像程序占位；无 source manifest | Gate D v01 全链 2 小时报废根因=近景质感欠账；**覆盖前置闸**（blocking 的 proxy 豁免必须与"不出现在高覆盖帧"绑定） |
| P5 | 绑骨 | **极限姿态下蒙皮变形成立 ≠ 骨架存在**（绕柱/穿建筑/扑镜/尾甩下不断裂不 candy-wrapper） | curve tube 冒充 rig；只有 skeleton/curve/path 无蒙皮多视图验证；插件模拟未 bake；穿建筑/台基/栏杆 | 项目最大的洞；pose board 必须 9 姿态×多视图（closeup↔近景球 / silhouette↔管形 / extreme bend↔candy-wrapper 逐条映射历史失败） |
| P6 | 动画 blocking | 镜头有意图 + 遮挡结构成立（P06 绕楼前后穿插 / P08 近镜头压迫），只验运动不追材质 | 龙只在楼旁飘；满屏遮挡读成 blob；速度曲线死板；镜头只缩放平移 | 必出 top/side/dragon-only 三路 playblast；motion 必须视频直读（kimi），静帧不构成 motion 证据 |
| P7 | 动画 polish | bake 后 clean render 一致 + 近景遮挡可读，不靠剪切藏丑 | 插件实时模拟直接进 final；动作靠剪切隐藏；最高覆盖帧不可读 | **每版一个假设、带假设重试；同层连败 2 次熔断出定向诊断板**（2D 22版/real-model 9版无诊断 churn 之戒；一张 touchdown 诊断板一次判掉三版） |
| P8 | 同源 pass | 每条 alpha 边缘来自真实对象 owner（同源 Blender 同时出 beauty+pass，不从 flattened MP4 反抠） | 从 flattened beauty 抠主 alpha；guide/SAM2/Seedance proxy 进 final slot；pass collection 空 | **Object/Material Index 只审计，不得作 final alpha**；覆盖阈值矛盾（jinxianmen>0.65 fail vs 天坛≥0.9 披露制）统一归 harness 的 audit_pass_outputs |
| P9 | 候选独立评审 | 高覆盖帧主体质感——**唯一真正抓住过 proxy 的位置** | 高覆盖帧像 proxy blob；龙再次读成球/管/capsule；技术能跑但视觉丑；没人审就进微信 | 评审契约版本化 + 动态直读 + 金反例回归（Gate D v01 金反例必须永远被判拒）；观察≠奖励，判定权归独立评审（自评通胀之戒） |
| P10 | 全长渲染 | 被 P9 正确阻塞才做全长；不能到全长才第一次看出模型问题 | 由 reduced candidate 未修复问题放大而来；full render 才发现模型病 | 定帧不过闸禁碰全渲；reduced 121 帧候选先行 |
| P11 | runtime 打包 | 只证 tracking/video-texture/SBS shader/重播/性能，**永不背书视觉** | offline 视觉闸未 accepted 就出 WeChat QR；临时签名 URL 当生产资源；test 资源进 prod | runtime smoke 被误当视觉验收 = Gate D v01 误传根因；"offline 未过→硬锁 QR"写进 checker |
| P12 | 生产发布 | prod 资源与 manifest 一致、可回滚、test/staging/prod 分离 | rejected v01/smoke 资源进生产；URL 是临时签名；产物无法溯源到 accepted gate | 登记才算存在（manifest 溯源） |

## A/V 合同（P1 边缘合同的扩展，每拍五列）

每拍 = **画面目标 / edge owner / 音乐动机 / 音效 / 台词 `[H-XX]`**。

- 声音绑定动作铁律：关键音效必须钉在具体动画动作上（空手倒茶之戒——没有对应动作的音效即穿帮）。
- P9 候选评审新增**音画合板 review**：评审必须带声看片（视频直读），静帧不构成 motion/音画证据。
- 八景磁贴音乐沿用**潮州音乐体系**，与该景 L2 动画同源 motif（磁贴版编曲可更轻快、玩具感）；声线锁童声 `zh-CN-YunxiaNeural`。

## 定帧赛马机制（创意层，复用 #136 §5–§6 模式）

Blender 微缩世界全渲太贵，**创意不做多 fork 全渲，用概念定帧赛马**：每候选 2–3 张成品级定帧（叠触发图合成后的"真机模拟帧"）→ tournament 择优 → **winner 才进 Blender 全流程**（"定帧先行"闸，V4 单图直接接 runtime 之败）。

- 编排（#136 §5）：G0 共享地基（单 agent 串行）→ 候选并行（各自 worktree 互不污染）→ tournament：phase Collect 汇总 → phase Judge 分闭包**盲评**（创意判官/史实顾问/生产可行官，禁看其他候选评语）→ phase Rank 主席**跨候选成对比较**（防呈现顺序锚定）+ 红线 GATE 一票否 → winner（允许杂交）+ 每候选可执行改进点。
- 择优阈值（#136 §6）：红线一票否 = 史实红线违反 / 加法光违反 / 长出点脱锚；相对排序维度 = 惊艳度与截图欲 / 与天坛差距 / anchor 专属性（换楼越不成立越好）/ 节奏成立度 / 生产成本风险。评委输入分层：先验给足（失败史+红线）/ 测量给足（boards）/ 自辩隔离（fork 设计说明标注"被审方陈述"）。

## proxy 生命周期（磁贴线复发重灾区）

- taxonomy：`guide_proxy` / `blocking_proxy` / `artist_approved_temp_final` / `final_asset`（改名不得绕闸）。
- 引入 proxy 的闸必须**同时声明退场闸**（升级为 final 的时点与验收）——Gate C ACCEPT 的 proxy 原样漏进 Gate D 之戒（执行 agent 自检已见问题仍按流程送审，因为没有闸让它停）。
- blocking 允许 proxy 的豁免**必须与"不出现在高覆盖帧"绑定**（否则 P4 覆盖前置闸失效）。

## 来源诚实机检

pass owner 的溯源资产 ID 由**遍历 .blend 对象推导**，不允许手写声明——acceptance-review 曾手写"visible real GLB"实为程序几何（手写声明可以说谎之戒）。source manifest / honesty statement 是 P4/P8/P9 交付物，机检不过即 reject。

## 分工指针（不复制，指名）

- **章程台账（权威 Phase 全文 + 逐条硬拒 + 磁贴对齐 comment）**：issue **#130**（每枚磁贴开 per-SKU 承接 issue，模式同 #136；金龙磁贴 = 本线爬坡 SKU，走 Gate D v02 preflight）。
- **作业环境（感知/行动/反馈三层 + 参数化渲染动词 + check-gate-status 聚合 + 金反例回归）**：issue **#131** + PR **#134** `tools/blender-harness/`（未合并，分支 `feat/blender-harness-foundation`）。
- **资产去处（渲染/boards/marker/GLB/音频/SBS 各落哪）**：`docs/architecture/ASSET_LAYOUT.md`（登记才算存在 → `docs/reference/ar-assets/manifest.json`）。
- **史料层与八景总纲**：issue **#135**（八景史料 comment，`[H-XX]` 锚）；**tournament 编排/择优阈值**：issue **#136** §5–§6；**混元图生3D 接力规则**：`.agents/skills/hunyuan-3d`（只作 source，不跳 Blender 闸）；**runtime 工程/SBS shader**：`.agents/skills/wechat-miniprogram-ar`（XR-Frame 引擎 API 见 skill `xr-frame`）。
