---
name: jygc-dragon-rig-pipeline
description: 揭阳古城 AR 中东方长身龙的领域合同、路线选择与高信息增益探针。用于龙、Loong、盘龙、龙绕楼、扑镜、龙三视图、Hunyuan 龙 source、组件拼接、retopo、UV、Spline IK/B-Bones、龙绑定或动画路线判断。它帮助判断“当前最危险的龙资产假设是什么、用哪个最便宜的 Blender/Hunyuan 探针证伪”，不规定固定 Phase/Gate 流水线。
---

# 揭阳古城东方长身龙

把本 skill 当作长龙领域专家，而不是生产状态机。先读目标画面和当前 RouteHypothesis，再选择与当前未知匹配的路线和探针。Harness 的路线、探针、证据与决策合同见 `docs/architecture/HARNESS_V1.md`；具体历史失败按需读 `docs/knowledge/AR_PRODUCTION_CASEBOOK.md`。

## Domain contract

- 可见龙必须读成连续、有生命的东方长身生物，而不是装饰过的 tube、capsule、rail、slab 或路径条带。
- 分开管理 **visual source** 与 **production control**：source 决定轮廓、头颈身、鳞/腹甲、鬃/鳍、爪、须、角和材质；control 决定拓扑、权重、rig、路径、owner 与可复现性。隐藏控制体可以简单，可见表面不能因此退化。
- Hunyuan、市场资产、程序几何和历史模块都只是 route input。供应商完成、预览好看或能绑定，不等于产品龙成立。
- 目标镜头决定质量压力。会近镜、盘绕、擦镜或占据大面积画面的部位，必须在相应距离和变形下证明连续性。
- 技术成功不能批准丑帧；worker 不为自己的最终可见资产签发产品结论。
- 第三方素材只有在许可、来源和再利用边界明确后才能进入生产 source。

项目默认美术方向是青玉/青绿、米白腹甲、珊瑚鬃、克制黄铜线的文化文创质感，避免通体金色玩具龙、西方翼龙或明显 stock dragon。若具体 Target Brief 另有方向，以 brief 为准。

## Route options

不要默认串行跑完所有选项。根据当前最危险的未知选一条，并写清推翻它的条件。

### A. Single-source full dragon

适合整体比例、身体节奏和头颈身连续性是首要风险时。用一致的完整设计图或完整 source 生成/制作整龙，再做 source-preserving cleanup 和生产拓扑。

优点：较早回答“是否是一条完整的龙”。风险：自动生成的背面、爪、尾、腹甲或拓扑仍可能不可用。

### B. Modular visual source

适合已有高质量头、爪、尾或纹样需要复用时。模块只能作为 source；在继续 rig 前，先证明接口、尺度、材质和鳞/腹甲流向在无 helper closeup 中连续。

如果 collar、鬃毛、socket 或相机角度只是遮住接缝，停止该路线或退回重新设计接口。参见 casebook `BH-002`。

### C. Manual or hybrid continuous body

适合生成 source 的整体形态可用，但需要人工连续身体、retopo、UV、lookdev 或局部雕刻时。允许 Hunyuan/采购件提供视觉参考，Blender/ZBrush/其他 DCC 建立最终连续表面。

### D. Licensed production asset adaptation

适合时间优先且存在许可明确、结构接近目标的长龙资产时。先验证授权、风格偏差、拓扑、rig 可改性和镜头适配成本；不要把 marketplace preview 当成项目验收。

### E. Control and motion route

仅在可见 source 足以支持目标画面后选择。长龙常用 Spline IK、B-Bones、curve controls，并为头、颌、须、鬃、爪和尾添加局部控制；这是一种成熟选项，不是唯一实现。

## Probe menu

每次只选择能最大幅度降低当前不确定性的最小集合。证据不足时 revise/abandon 路线，不要为“走完流程”继续。

| 当前问题 | 最便宜的探针 | 证据 | 停止/改路信号 |
| --- | --- | --- | --- |
| 设计是不是一条完整东方龙 | source-sheet consistency probe | front/side/back/top/hero 关键对应点；头身比例、四肢、腹甲、背部节奏标注 | 多视图互相矛盾；身体太短；西方龙/玩具龙读法 |
| 头、颈、身是否连续 | no-helper continuity probe | 头颈、腹侧、背侧、尾根的真实材质 closeup；禁用 collar/helper 后的视图 | 接缝、硬 socket、鳞流/腹甲断裂；只能靠遮挡成立 |
| source 是否值得生产化 | raw import probe | 可解码 raw、来源 hash、真实 Blender import、轮廓/背面/爪/尾 closeup | 只有 URL/preview；背面或关键部件不可修；成本超过重做 |
| 拓扑是否支持目标动作 | deformation-topology probe | wireframe + 目标弯曲区局部变形；腹甲和背鳍在 bend 中的连续证据 | candy-wrapper、压扁、环线/三角分布破坏轮廓 |
| rig 方案是否可控 | extreme-motion probe | 从目标镜头反推的 S/C curve、coil、wrap、lunge 或 head aim 中最危险的 2–3 个动作 | twist、穿模、爪漂移、尾根断裂、bake 后不一致 |
| 动画是否像龙而非路径物体 | motion-reading probe | 带时间的 main/top/side 或 asset-only 小段；头身波、follow-through、深度关系 | 整体匀速平移；身体仍像管；主视角靠遮挡隐藏问题 |
| 近镜是否能进入产品 | peak-frame probe | 目标分辨率下最接近镜头的短片/密集帧和材质 closeup | proxy/blob、头小身大、鳞/腹甲/鬃在运动中崩坏 |
| pass/runtime 能否保持真实 owner | ownership probe | 从 `.blend`/scene 推导对象和 owner；beauty/matte 对账 | 手写声明与 scene 不符；背景/非龙区域进入 alpha |

探针视图由问题决定，不要求每次输出固定全集。单帧只回答静态形态；motion 必须用视频或足够密集的时间证据。

## Route decisions

- `continue`：当前探针支持路线假设，且下一高风险未知已明确。
- `revise`：方向仍成立，但接口、source、拓扑或控制策略要变；记录 Deviation。
- `abandon`：核心前提被击穿，例如模块无法形成连续可见生物。
- `ask_owner`：美术方向、许可、成本或产品目标需要 owner 选择。

不要使用“accepted”概括局部技术 proof。写清它只证明了什么、仍未证明什么、允许的下一行动是什么。

## Knowledge and storage pointers

- Hunyuan 当前能力与输出边界：`docs/integrations/HUNYUAN.md`。
- 资产来源与重资产位置：`docs/architecture/ASSET_LAYOUT.md`。
- 旧模块龙、Gate D proxy、P41 路线重置等证据：`docs/knowledge/AR_PRODUCTION_CASEBOOK.md` 的 `BH-001`、`BH-002`、`HY-003`。
