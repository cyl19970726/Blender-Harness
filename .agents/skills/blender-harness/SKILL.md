---
name: blender-harness
description: 揭阳古城 AR 内容产线在 Blender 里做动画生产的作业环境(harness)本体。当任务涉及:用 Blender 预渲染磁贴/印章卡(卡面合同)或景点效果层(景点合同)、给模型/绑骨/动画/pass 做多视图板验收、跑评审闸放行下一阶段、check-gate-status / gate-status.json 判定、金反例(golden negative)回归、候选(candidate)验收目录契约、写或改判定器 checker、参数化渲染动词、感知/行动/反馈三层、内环 quicklook 外环 board —— 时使用本 skill。出现 harness / gate-status / 多视图板 / 评审闸 / golden negative / 候选验收 / Blender 生产 / .artifacts / 熔断 等关键词也应触发。它给的是"怎么用这套作业环境+不变量+硬拒清单",不是 Blender bpy 教程(bpy/retarget/导出见 blender-mcp;3D 角色总管线见 ar-3d-pipeline;景点合同落地见 scenic-spot-ar;磁贴创意见 ar-fridge-magnet)。
---

# Blender Harness 作业环境

给未来在本仓做任何动画生产的 agent:这不是"渲染完跑一下"的 QA,而是 **agent 在 headless Blender 里的作业环境**。headless Blender 里 agent 天然是盲的(能跑 bpy,看不见 viewport),所以每一步都要靠这套环境的"眼睛"和"闸"来推进。

权威指针(细节全在这里,本 skill 不复制):harness 本体设计见 **issue #131 正文**;仓库落点/包结构/动词表/退出码/fixtures 见 **`tools/blender-harness/README.md`(main-base PR #152)**;目录/资产契约见 **`docs/ASSET_LAYOUT.md`**;生产宪法(Phase+Gate)见 **issue #130**。

## 核心约束:观察 ≠ 奖励

agent 用自己的眼睛(感知层)干活,但**通过权只在独立评审手里,不在生产者自己手里**。作者自审通胀已被历史证实——"栏杆不咬合"从 v04 活到 v09,每版自评"比上一版好"。所以:感知层是你的工作工具,`metrics 只有拒绝权`,晋级签发只出自被引用的 `reviews/*.json`。

## 三层架构

| 层 | 是什么 | 交付物 | runtime |
|---|---|---|---|
| 感知层(眼) | 固定多视图 / board / filmstrip / 参考并排 | 内环 quicklook + 外环正式 board | `blender -b --python` |
| 行动层(手) | 参数化脚本动词;插件=动词扩展 | `blender/render_*` / `blender/audit_*` / `package_sbs_alpha` | `blender -b` / `python3` |
| 反馈层(判定) | gate 状态机 + 聚合判定 + 金反例回归 | 双 schema + `check-gate-status.mjs` + regression | `node`(零依赖,进 CI) |

分层是结构性约束:**反馈层纯 node、无 Blender 依赖、每个 PR 进 CI 自动跑**;行动/感知层要 `blender -b`,不进 CI,只在本机/渲染节点执行。反馈层刻意最先构建——没有能真正拒绝产物的判定器,拍再多板子也只是装饰。动词全表(render_model_multiview / render_rig_pose_board / render_animation_multiview / build_source_pass_view_layers / render_source_passes / audit_pass_outputs / package_sbs_alpha / quicklook + `blender/lib/` 公共件)见 README 动词表;PR #134 只落了反馈层,感知/行动层为 PR-3 占位。

## 内环 / 外环

- **内环**:worker 干活时随手看。秒级~分钟级、单命令、无仪式、任意工作状态可调用(`quicklook`)。"内环好用"(快/可组合/随时可调)是脚本的验收标准之一,不只是"视图齐全"。
- **外环**:阶段边界正式验收。固定视图全集 + 独立评审 + 参考并排 + `gate-status.json` 落盘 + 下游物理阻塞。
- 同一批渲染脚本服务两个环。落地顺序按"历史失败对应的视图优先":closeup/silhouette(近景低模球/管)→ skinned deformation pose board → top/side/dragon-only → 高覆盖帧 contact sheet(f072/f116/f117)。

## 执行单元模板(每个 Gate/Phase = 一个 workflow)

```text
worker agents 执行阶段产物(headless + 插件动词;↻ 内环 quicklook 速览自查)
  → 参数化脚本出多视图板(固定视图 + 固定帧 + 参考并排)
  → specialist reviewer(只审本阶段维度,有权 reject)
    ∥ fresh visual reviewer(先验足 · 测量足 · 自辩隔离)
  → check-gate-status 聚合判定 → gate-status.json 落盘
  → PASS: downstream_allowed=true,解锁下一 phase
  → FAIL: 物理阻塞下游 → 诊断归因 → 回本层或上游层重跑
       同层连败 2 次 → 熔断:先出定向诊断板 + 用户 checkpoint,禁盲目重试
```

铁律:
- **失败先归因再路由**,不一定回本阶段(Gate D v01 在候选阶段暴露,修复全是模型/rig 层工作)。
- **每次重跑必须声明假设**:"这版改了什么、预期哪个视图变好"。带假设重试。
- **reviewer 必须能 reject**,不能只写"建议优化"。

## 多资产构建模式

这个 skill 的目标不是"做龙",而是给未来多个 Blender 资产建立同一套生产 OS。龙只是 `long_creature` 的复杂生物样例;揭小贤、郭之奇、建筑件、产品道具也必须走同一套 candidate / evidence / review / gate 纪律。

当任务是"做一个 3D 资产 / 角色 / 建筑 / 道具 / 动画 / source-pass"时,先不要打开 Blender 乱修。先完成四个选择:

1. **资产 profile**:从 `tools/blender-harness/profiles/asset-profiles.json` 选择 `long_creature` / `humanoid_character` / `historical_figure` / `building_prop` / `product_prop`。没有合适 profile 时,先扩 profile,不要硬套。
2. **当前 gate**:明确现在是在 `asset_art` / `topology_uv` / `rig_deformation` / `animation` / `source_pass` 哪一层。不能用后层修前层问题。
3. **candidate 目录**:每个候选必须有 manifest、evidence、reviews、gate-status;不能只靠聊天或单张截图。
4. **Human / Agent review 合同**:每个 gate 必须引用版本化 prompt 和 rubric;reviewer 必须有 reject 权。

### 资产存储边界

Blender harness 不能脱离资产存储纪律运行。做任何 candidate 前先按 `docs/ASSET_LAYOUT.md` 判断文件落点:

| 位置 | 放什么 | 是否进 Git |
|---|---|---|
| `_assets-src/<asset-id>/` | 轻量权威源:brief、三视图、配饰拆分、ownership matrix、`PROVENANCE.md`、source manifest | 是,前提是小文件且来源清楚 |
| `.artifacts/blender-harness/<candidate-id>/` | 全量候选:raw `.blend`、渲染板、帧序列、工作中间产物、失败候选 | 否 |
| `.artifacts/hunyuan/<asset-id>/<run-id>/` | Hunyuan raw/postprocess 输出、下载的 GLB/OBJ、run manifest | 否 |
| `docs/research/.../<candidate>/` | gate 关闭后的轻量证据:boards、audit、review JSON、summary | 是 |
| CloudBase/COS/GitHub Release | 需要长期保存或 runtime 使用的大二进制 | Git 只记 URL/SHA256/size/provenance |
| `wechat-*/miniprogram/**/assets/` | 小程序包内 runtime 小资产 | 是,但必须先有包体和 manifest 决策 |

Git 保存权威轻量源、文档、manifest 和验收板;大资产走 `.artifacts` + CloudBase/COS/GitHub Release。不要默认启用 Git LFS;LFS 是单独的 repo 级大文件版本策略,没有明确决定前不得把 `.blend`/raw GLB/视频塞进 Git。没有 `PROVENANCE.md`、SHA256 或 manifest 记录的大资产,在生产上等于不存在。

### 通用 Phase

用于 STAR/harness goal 时,任何复杂资产都应拆成这些顺序 phase。简单道具可以合并 phase,但不能跳过对应 gate 的证据和评审。

| Phase | 适用 profile | 目标 | 关键产物 |
|---|---|---|---|
| `p0-process-lock` | all | 锁定 profile、gate、目录、prompt、review 角色、禁止越级 | Goal / phase acceptance / skill or README link |
| `p1-reference-art-direction` | all | 参考研究、风格、比例、用途、授权、运动/展示目标 | reference board / source notes / art decision |
| `p2-source-design` | all | 资产设计先成立;复杂角色必须从设计阶段证明结构关系 | design sheets / closeups / profile-specific callouts |
| `p3-source-surface` | all | 生成、购买、手工或混合 source,但 final source 必须可审 | source-manifest / material-clay-wire-closeup boards |
| `p4-retopo-uv-material` | deforming profiles | 拓扑、UV、bake、材质连续;静态建筑/道具则看硬边/UV/材质 | topology / UV / texel / bake boards |
| `p5-rig-deformation` | animated profiles | 绑定、控制器、极限姿态、closeup deformation | rig hierarchy / pose boards / skin-weight audit |
| `p6-animation-blocking-polish` | animated assets | 多视图验证 motion、camera、遮挡、节奏 | playblast / camera-top-side-asset boards |
| `p7-source-pass-runtime` | AR outputs | 同源 beauty/pass/matte,再 runtime/CloudBase/真机 | owner manifest / matte boards / runtime boundary audit |

### Profile 路由

| Profile | 典型资产 | 最容易失败的位置 | 必须优先看的板 |
|---|---|---|---|
| `long_creature` | 龙、长蛇形生物 | source 连续性、管状身体、盘绕/扑镜变形 | head-neck / belly-dorsal / tail-root / coil-lunge closeup |
| `humanoid_character` | 揭小贤、IP 人物 | 脸不像、手塌、服装/配饰不跟随、retarget 丢性格 | face / hands / outfit / accessory / expression |
| `historical_figure` | 郭之奇等历史人物 | 年代服饰错、气质不对、袍袖/手势崩 | face-age-dignity / costume / robe-sleeve / cultural tone |
| `building_prop` | 城门、台基、栏杆、门框 | 结构不咬合、硬边法线脏、锚点/尺度错 | structure join / hard-edge normal / scale anchor |
| `product_prop` | 冰箱贴、茶具、食物、文创道具 | 近景材质低、边缘脏、产品尺度不稳 | product edge / material finish / marker scale |

### 候选目录和证据

每个真实候选至少要有:

```text
candidate-manifest.json
artifact-manifest.json
prompt-manifest.json
source-manifest.json
evidence/
reviews/
gate-status.json
```

`check-artifacts` 先看 evidence / prompt 是否齐全;`check-gate-status` 再看 reviews / status / downstream 是否一致。若有 `prompt-manifest.json`,每个 review 必须引用其中声明的 `prompt_id`;没有 prompt-bound review 的通过记录不算正式 gate。

### Human / Agent / Subagent 角色合同

需要 subagent 时,它们只能在正式主线程或支持 subagent 的执行环境里运行。side conversation 不能实际调用 subagent。即便如此,Goal 和候选必须预留这些角色,让后续执行可复现。

| 工作层 | Worker 角色 | Reviewer 角色 |
|---|---|---|
| Reference | reference researcher / license researcher | art director / provenance reviewer |
| Asset Art | concept/source/model worker | asset_art_reviewer / fresh_visual_reviewer |
| Topology / UV | retopo worker / UV-material worker | topology_reviewer / uv_material_reviewer |
| Rig / Deformation | rig worker / deformation board worker | rig_reviewer / deformation_reviewer / fresh_visual_reviewer |
| Animation | animation worker / camera worker | animation_reviewer / fresh_visual_reviewer |
| Source-Pass | pass worker / runtime packager | source_pass_reviewer / runtime_boundary_reviewer / fresh_visual_reviewer |
| Global | observer,不生产资产 | 跑偏检查:是否把上游问题推给下游、是否假绿 |

### 复杂生物样例:Long Dragon

龙是 `long_creature` 的复杂生物样例和 canary,不是这个 harness 的唯一目标。它用于验证 harness 能不能拦住 source 阶段失败,尤其是:

- `head_neck_body_seam_visible`
- `decorated_tube_or_slab_body`
- `helper_collar_or_socket_masks_art_failure`
- `scale_or_belly_flow_breaks_at_neck_or_tail`
- `coil_or_lunge_closeup_collapses`
- `camera_hides_asset_failure`

详细样例见 `tools/blender-harness/examples/complex-creature-long-dragon.md`。任何阶段发现"头 + 管子身体 + collar/鬃毛遮缝"都必须在当前 gate reject,并回到 source design 或 source surface;不得继续 retopo、UV、rig、动画、source-pass 或 runtime。

### Humanoid IP 样例:Jie Xiaoxian

揭小贤是 `humanoid_character` 的 IP 角色样例,当前只作为流程示例,**未完整验证为生产资产**。它用于说明从概念图/三视图/Hunyuan source 到 Blender cleanup、retopo、UV/material、rig/deformation、gesture animation 的 gate 纪律。

详细样例见 `tools/blender-harness/examples/humanoid-ip-jie-xiaoxian.md`。它和长龙最大的区别是:揭小贤可以有衣服、头发、眼睛、配饰、道具等多 part 资产,核心风险是脸、比例、手、袖子、配饰和 retarget 后的 IP 性格;长龙的核心风险是头颈身体必须是连续生物、长身体 topology/UV/rig 必须支持盘绕和扑镜。

### 路由规则

- Asset Art 失败 -> 回 reference/source design/source surface,不是 retopo/rig/animation 修。
- Topology / UV 失败 -> 回 retopo/UV/material,除非暴露 source 设计问题,则回 Asset Art。
- Rig / deformation 失败 -> 回 rig/weights/control,若 mesh loop 不支持变形,回 Topology。
- Animation 失败 -> 先判断是 motion 问题还是 asset/rig 问题;不能用 camera 遮前层失败。
- Source-pass 失败 -> 回 scene ownership/pass layer;不同源 matte 禁进 final。
- Runtime 失败 -> 只修 runtime/packaging/性能;不能把 runtime smoke 当视觉 acceptance。

## check-gate-status:用法与 exit 语义

```bash
node src/check-gate-status.mjs <candidate-dir>
node src/check-gate-status.mjs <candidate-dir> --json
```

`<candidate-dir>` 是**参数**(禁硬编码具体候选路径)。目录内必须有 `gate-status.json`,以及 `reviews[].file` 指向的每个 review 文件。退出码:

- **`0` = accepted**:status 属 accepted 族(`accepted` / `production_accepted`),且每个 `required_reviews` 角色都有一条 `verdict: accept` 的 review。**exit 0 只代表"评审记录齐全、结构合法、且全部 accept",不代表视觉背书**——视觉背书只在被引用的 `reviews/*.json` 内部。
- **`1` = rejected / blocked**:任一 required review 缺失、任一 required `verdict` 为 `reject` 或 `conditional`、status 不是 accepted 族、或 `forbidden_next_outputs` 命中。
- **`2` = 契约违规或输入缺失**:`gate-status.json`/`review.json` 缺失或不符合 schema 形状,或 `status` 与 `downstream_allowed` 内部不一致。**状态机本身撒谎比某次评审没过关更严重**,所以单列 exit 2。

### 聚合规则六条(checker 硬编码,不做成可配置项)

1. 任一 `required_reviews` 角色在 `reviews[]` 中缺失 ⇒ rejected(exit 1)。
2. 任一 required review `verdict: reject` ⇒ rejected(exit 1);`verdict: conditional` **不解锁下游**,同样 rejected(exit 1),但诊断消息与 reject 区分(区分"硬拒"还是"有条件未过关")。
3. `status` 与 `downstream_allowed` 必须方向一致:accepted 族 ⇔ `true`,非 accepted 族 ⇔ `false`。任一方向不一致 = **契约违规(exit 2)**。
4. `runtime_smoke_passed` **永不**等价/自动升级为 `production_accepted`(只证微信 runtime 能加载候选,不是生产验收);若该 status 却 `downstream_allowed: true`,按规则 3 判契约违规。
5. `forbidden_next_outputs` 中任一路径/glob 在候选目录内实际存在、且候选未处于 accepted 状态 ⇒ rejected(exit 1)。这是防"评审没过但下游产物被手工塞进候选目录"的物理绕过。
6. 退出码总表:`0`=accepted / `1`=rejected/blocked / `2`=契约违规或输入缺失。**metrics 只有拒绝权**:checker 能阻断晋级,不能替独立评审签发"好看"。

## 金反例回归纪律

`fixtures/gate-d-v01-negative/` 是**金反例**:真实 Gate D 121 帧候选,独立视觉评审已判 REJECT(高覆盖帧读成低模代理球/管,而非叙事驱动的龙形遮挡)。

> **改 checker 必须仍判拒 v01。** 任何让金反例变成 accepted 或 `downstream_allowed: true` 的实现,是 checker 的 bug,不是 fixture 的 bug。`npm test`(`cd tools/blender-harness && npm test`)对金反例 + 正控(`synthetic-accepted-control`)+ 两条 tmpdir 篡改拷贝跑 4 条回归断言;CI(`.github/workflows/blender-harness.yml`)用同一条命令。改了聚合逻辑,先跑 `npm test` 绿了才提交。

历史洞:早期 check 脚本对 v01 只是"状态一致性通过",从未真正判拒过任何产物——这曾是机器层最大的洞。金反例的交付定义是"check-gate-status 跑 v01 输出 rejected 的日志"(`v01_regression_result.md`),不是"v01 目录存在"。

## 两种输出合同的产物目录契约

权威表见 `docs/ASSET_LAYOUT.md` §1。要点:

- **全量渲染产物** → `.artifacts/blender-harness/<candidate-id>/`(gitignored,任意大,不进 git)。每 candidate 一个独立目录,内部阶段化:`00_inputs/`(manifest.json + reference/ + source_assets/)、`01_model_multiview/`、`02_rig_validation/`、`03_animation_blocking/`、`04_animation_polish/`、`05_source_pass/`(beauty/ + object_mattes/ + audit/)、`06_reduced_candidate/`(runtime_media/)、`reviews/`、`gate-status.json`。逐阶段字段见 issue #131《目录结构》。
- **轻量判读证据**(boards / audit.json / *-review.json) → gate 出结果时归档进 `docs/research/ar-magnet/<slug>/<candidate>/`(进 git,只放评审用的板/截图/JSON,不放全量渲染)。
- **金反例** → `tools/blender-harness/fixtures/`(每个一子目录 + `README.md` 说明"为什么必须永远被拒")。
- **发布视频**(SBS/加法层,超小程序 2MB) → CloudBase,manifest 记 URL + SHA256。**runtime GLB ≤ 2MB**。

两种合同的产物形态不同,同一套目录/闸复用:
- **卡面合同**(磁贴/印章卡=手持平面物):微缩世界 + 虚拟运镜 + 扑镜满屏(天坛语法)。质量之王=扑镜物峰值入镜覆盖(Gate D v01 死于 f072/f116/f117 proxy 盖屏)。
- **景点合同**(扫真楼):**固定机位效果层,无运镜**(视频里运镜=穿帮);光效=黑底加法层(add blend 黑即透明),实体=SBS alpha;效果必须从真楼具体部位长出。

`status` 单源:`gate-status.json` 是唯一权威状态,人读文档由它生成(历史:状态 6–8 处手工镜像,checker 三次抓到漂移)。

## 评审契约要点(fresh visual reviewer)

`rubric` 冻结为版本化文件(`reviews/rubric-vNN.md` / README 后续的 `rubrics/rubric-v01.md`),每次评审引用版本号,**不得现写 prompt**。硬拒条款 = 历史失败模式蒸馏,每次 REJECT 沉淀新条款。

- **默认拒绝**:先验写死"不要默认通过",候选工件自带 blocking 状态。
- **输入分层(反全盲)**:先验给足(失败模式清单:slab 竖窗 / proxy 冒充 final / 悬浮 / 低模球管)+ 测量给足(audit 的 high_coverage_frames 作注意力导航,**metrics 只指路永不构成通过证据**)+ **自辩隔离**(候选方自己写的解释必须标注"被审方陈述",不得作通过依据)。
- **参考并排强制**:判词必须附"参考帧 vs 候选帧"对照证据——"丑"只有并排才成为可复核事实。
- **motion 必须视频直读**(kimi 直读或密集帧条):**单帧静态姿势 ≠ 动画**;静帧不构成 motion 维度证据(v01 评审 motion 3/5 实际无动态依据)。空手倒茶之戒——声音/动作绑定要在动态里核。
- **输出四问契约**:过不过 / 为什么(引用具体帧) / 下游动不动 / 下轮改什么。分数要么有档位锚点要么删(v01 判词里数字分与决策脱钩,真正做功的是硬拒条款命中列表)。
- 保留必答问题:是否像高级 AR 磁贴 / 哪帧最丑 / 哪帧最像 reference / 技术能跑但视觉丑即拒。

## 参数化铁律

一切 render / board / audit / check 脚本必须以 `asset-id` / `gate-id` / `candidate-dir` 为**参数**,禁再造 per-artifact 硬编码脚本。历史:42+ 个一次性脚本(grep argv 零命中)= 没有稳定动作空间,每个任务重新发明动词;两套 audit 语义分叉。**插件/脚本是动词扩展,不是一次性用具。**

配套两条:
- **眼睛与 runtime 对账**:harness 渲染参数(分辨率/色彩管理/相机)必须可证与最终渲染一致——验证器分叉曾致连续多轮误判(scene_verify 2× 缩放 bug、绝对赋值冲掉 GLB 嵌套 scale 之戒)。
- **来源诚实机检**:pass owner 溯源资产 ID 由 `.blend` 遍历推导,**手写声明会说谎**(acceptance 撒谎之戒)。

## 熔断纪律

- **同层连败 2 次 ⇒ 熔断**:停手,先出一张**定向诊断板** + 用户 checkpoint,禁盲目重试(一张定向诊断板顶五轮盲调;touchdown 诊断板一次判掉 v06–v08)。
- **死范式熔断**:2D 22 版 / real-model 9 版之戒——反复撞同一范式要换范式,不是加版本号。
- **每版一个假设**,带假设重试;没有假设的重试不算进度。
- **proxy 生命周期**:引入即声明退场闸(Gate C ACCEPT 的 proxy 原样漏进 Gate D 之戒);proxy 命名为 final = 硬拒。
- **定帧先行**:定帧不过闸禁碰 runtime(V4 单图接 runtime 之败);创意用定帧赛马,不做多 fork 全渲。
- **完备而不虚胖**:每类交付物必写明消费者(谁读它、谁因它被阻断);没有 checker/reviewer 消费的 board 是装饰。

## 红线继承

加法光铁律=不透明层禁盖死实时相机(景点合同尤甚);三类图严格分开(参考图不进产品/触发图=实拍锚点/动画美术图=overlay);神庙类不显灵不祈福不塑神临现。细节见 `scenic-spot-ar` 与 issue #135。
