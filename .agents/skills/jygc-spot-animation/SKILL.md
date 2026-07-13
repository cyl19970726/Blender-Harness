---
name: jygc-spot-animation
description: 揭阳古城真实景点 AR 效果层的领域合同、路线选择与探针菜单。用于扫真楼、景点打卡动画、触发图、photo-match/fSpy、固定效果相机、长出点、黑底加法光、SBS alpha、实时 3D、composite preview、史实和宗教表达检查。它帮助选择配准、可分解性、合成、内容或真机 probe，不规定固定六拍、G0 四件套、300 帧或 tournament 流水线。
---

# 揭阳古城真实景点 AR

本 skill 负责真实建筑与效果层之间的产品合同。Harness 的路线、探针和证据结构见 `docs/architecture/HARNESS_V1.md`；历史失败按需读 `docs/knowledge/AR_PRODUCTION_CASEBOOK.md`。

## Domain contract

- 真实相机里的建筑是主体。效果应从门洞、匾额、檐角、石缝、窗、地面或其他可识别部位“长出”，而不是浮在屏幕中央的贴纸。
- 对预渲染效果层，主触发图/photo-match 默认构成效果相机合同。视频自身的推拉摇移会与用户手机运动冲突；若要突破固定效果相机，必须提出能解释真实相机运动的新跟踪/实时渲染路线并先做真机 probe。
- 光效通常用黑底 additive 层，只增加光；有实体轮廓的贤士、灯笼、文字、卷轴或道具使用带 alpha 的媒体或实时 3D。不要用不透明全帧重绘盖住实时相机。
- 评审看 `effect + trigger/live-camera` 的 composite preview，不只看裸效果层或完整离线视频。
- 参考图、实拍触发图和动画美术图属于不同来源类型，必须保持 provenance 和物理分离。
- 技术合成通过不等于美术、史实或文化表达通过。
- 神庙、佛寺、学宫相关内容默认不显灵、不祈福、不塑神临现；只做民俗、文化、修心或劝善表达。

打卡完成时是否浮出印章、如何触发服务端 check-in、是否进入纪念态，由当前产品 brief 决定；它不是所有视觉 probe 的前置手续。

## Route options

### A. Additive light plate

适合鎏金、声波、晓光、灯河、雷光、粒子和体积光。需要证明黑底、混合模式、曝光和真机相机不会产生灰底、盖楼或颜色漂移。

### B. Alpha entity plate

适合有实体边缘和遮挡的角色、灯笼、卷轴、题字或道具。可用 SBS alpha 或平台支持的其他透明媒体；关键是边缘、颜色和 alpha 同步。

### C. Realtime 3D/effect

适合需要随真实相机视角变化、深度遮挡或交互的内容。先验证 tracking、坐标、性能、包体和材质，不因已有 GLB 而默认采用。

### D. Hybrid decomposition

允许 additive light、alpha entity、实时元素和 UI 分层组合。先写每层 owner、合成顺序、相机关系和可接受误差。

### E. Generated element route

AI 视频/图像可以作为单元素、纹理、氛围或 motion source。全帧生成只有在背景可被可靠分解并叠回真实相机时才可作为 live overlay；否则只作目标帧或参考。

## Probe menu

| 当前未知 | 最便宜的探针 | 需要看到 | 改路信号 |
| --- | --- | --- | --- |
| 触发图是否能支持生产 | trigger-source probe | 原片、EXIF/焦距/机位、遮挡与光照检查、provenance | 分辨率/视角不足；人流遮挡关键部位；来源不明 |
| 效果能否贴住建筑 | registration probe | photo-match 相机；少量代理几何；线框/锚点叠触发图 | 关键檐角/门洞明显漂移；误差无法由当前路线解释 |
| 效果是否从这座楼长出 | anchor probe | 1–3 张 composite 目标帧；标注长出点和遮挡关系 | 换楼仍成立；浮空贴纸；只靠屏幕中心构图 |
| 输出能否叠回 live camera | decomposition probe | additive/alpha/realtime 各层 + 重构/composite 对照 | 背景重绘残留；楼身进入实体 alpha；灰底或不透明盖楼 |
| 虚拟相机是否与手机冲突 | camera probe | 短真机录屏或模拟真实相机扰动 | 效果相机和手机运动叠加后滑动、穿帮 |
| 光/实体是否达到目标质感 | lookdev probe | 最小关键镜头；尺度、材质、辉光、接触光和阴影 | machine-correct 但仍“小气”、PPT 贴纸或无场景光融合 |
| 内容是否可发布 | history/culture probe | 每个具名人物、诗句、匾额、年份和宗教动作的来源 | 无依据杜撰；显灵/祈福/塑神；人物或地名错误 |
| A/V 是否咬合 | cue probe | 带声短片与关键动作时间 | 音效空响；声音与长出点/动作不对应 |
| runtime 合成是否成立 | device smoke | 真机 tracking、blend、重播、性能和曝光 | 技术失败；技术通过仍不批准创意或内容 |

代理白模只用于 photo-match、发射面、遮挡和诊断；默认不作为可见建筑。探针视图、帧率、时长和分辨率由 Target Brief 决定，不固定为 24fps、12.5 秒或 300 帧。

## Content anchors

以下是项目内容 policy，不是 Blender validator：

- **进贤门**：郭之奇绝命诗系伪作禁用；可考诗句包括《朝旭》“怪来朝旭起，云岫敛清晖”；无可考楹联和石匾题写者不得杜撰。
- **城隍庙**：没有“明镜高悬”匾；可核史料包括双匾“你来了么”“也有今日”。只做劝善民俗。
- **揭阳学宫**：不拜孔像、不做孔子显灵；可做文教民俗。
- **双峰寺**：不显灵、不祈福；可做晚钟、禅光和修心表达。
- **石狮桥**：年份不写死；行彩桥与青狮“安澜”点位不要混用。
- **雷神殿**：人物名“胡鹤翥”；表达感恩，不塑雷神显灵。

具体史料以项目权威内容卡为准。若内容卡与本摘要冲突，先 `ask_owner` 并更新权威来源，不要自行补故事。

## Creative selection

定帧赛马、多候选并行和 tournament 可用于高成本、方向差异大的创意选择，但不是每个景点的固定前置流程。先共享那些会影响可比性的事实（同一触发图、目标画幅和发布合同），再决定是否需要多个候选。不要强制每条路线共享同一种实现、帧数或 rubric。

## Pointers

- 触发图、marker、源资产与发布媒体位置：`docs/architecture/ASSET_LAYOUT.md`。
- Hunyuan 只在路线选择需要时使用：`docs/integrations/HUNYUAN.md`。
- 全帧 AI 不可分解、真实相机与虚拟运镜冲突、手搭光效观感不足、临时触发图、史实与音画案例：`docs/knowledge/AR_PRODUCTION_CASEBOOK.md` 的 `SPOT-001`、`SPOT-002`、`SPOT-003`、`SPOT-004`、`CONTENT-001`、`AUDIO-001`。
