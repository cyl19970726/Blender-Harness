---
name: blender-harness
description: 揭阳古城 Blender 长程资产与动画任务的 adaptive harness。当任务涉及 Harness、路线选择、执行中改路线、RouteHypothesis、ProbeRun、Quicklook、多视图证据、独立评审、Blender headless 作业、Hunyuan 候选进入 Blender、揭小贤素体/绑骨/服装/动作，或需要判断哪些内容该做 machine gate、agent review、casebook 时使用。核心不是固定 Phase 流水线，而是目标画面→可证伪路线→小探针→证据→继续/修改/放弃/请求 owner。
---

# Blender Harness v1

## 先读

- `README.md`
- `docs/architecture/HARNESS_V1.md`
- 当前任务若是揭小贤里程碑，再读 `docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md`
- 若调用混元，再使用 `hunyuan-3d` skill 和 `docs/integrations/HUNYUAN.md`

旧 `tools/blender-harness`、固定 profile、通用 Phase/Gate 表、`gate-status.json` checker 和 golden-negative fixture 已被 ADR-0008 替换。不要引用已删除路径，也不要重建 v0 兼容层。

## 工作原则

1. 先写最终目标画面和不可牺牲项，不从“有哪些脚本”反推路线。
2. 把当前路线写成 RouteHypothesis：假设、未知、停止条件、替代路线、预算和最便宜证伪方法。
3. 高成本步骤之前先跑不可发布 ProbeRun。探针可以粗糙，但问题必须单一、预算有限、证据预期明确。
4. 执行必须产生可复现 run：输入 SHA256、Blender/供应商版本、命令、日志、manifest 和真实媒体。
5. Probe 必须先进入终态并留下证据，才能做 RouteDecision。
6. 前提被击穿时禁止 `continue`；选择 `revise`、`abandon` 或 `ask_owner`。
7. provider `DONE`、Blender exit 0、骨架存在、文件能打开都不等于资产 approved。

## 机器与 agent 的边界

机器只判断真实性和状态不变量：文件/哈希/格式/状态/证据/来源、探针不可发布、前提击穿不能继续、缓存未被篡改。

Agent/human 判断目标是否成立：脸和轮廓、近景表面、拓扑与变形、穿模、动作语义、镜头节奏、历史/文化语义、局部修复还是推翻路线。

不要把一次失败的外观特征硬编码成所有资产的 gate。只有跨资产稳定且能机械观测的不变量才能进入 validator。

## Multi-agent 合同

- Director：拥有 target brief 和最终画面，不生产资产。
- Route Scout：提出 2–3 条路线和最便宜探针，不批准输出。
- Worker：在选定路线内执行 Blender/provider run，不自签通过。
- Specialist：只在当前瓶颈属于其领域时介入，例如 topology、rig、cloth、lookdev。
- Visual Critic：基于 target frames 与证据给 continue/revise/abandon 建议。
- Archivist：决定新发现进入 validator、domain knowledge、casebook 或不固化。

多 agent 用在高信息增益与分歧节点，不对每一步强制投票。若角色意见冲突，保留各自理由与证据，交 Director 或 owner。

## CLI

```bash
bh doctor --blender /opt/homebrew/bin/blender
bh quicklook model.glb --intent "检查脸、肩和胯" --blender /opt/homebrew/bin/blender
bh route init ...
bh probe create ...
bh probe finish ...
bh route decide ...
bh deviation add ...
bh hunyuan capabilities
```

Quicklook 是内环感知，不是视觉批准。正式判断应引用目标帧、必要的专项板和 run manifest。

## 旧经验如何接入

读取 `docs/knowledge/LEGACY_SKILL_MIGRATION.md`。龙、磁贴、景点 skills 是领域知识库，不是 Harness 状态机。使用其中失败经验时先问：

- 它是否适用于当前资产和最终画面？
- 它是可机检不变量、路线风险提示，还是一次性 case？
- 最便宜的当前项目证伪探针是什么？

只有回答完这三问，旧经验才能影响当前路线。
