# ADR-0008：用 evidence-first Harness v1 替换 case-heavy v0

- 状态：Accepted
- 日期：2026-07-13

## 背景

旧实现把大量具体失败案例、rubric 和 fixture 编译成通用 gate。它能稳定重放已知 case，却不能回答长程 Blender 工作最关键的问题：当前路线假设是否仍成立，以及发现新问题后是否应该修改路线。结果是“通过脚本”逐渐取代“最终画面成立”。

## 决策

删除 `tools/blender-harness` v0，建立 Python 3.9+ 的 Harness v1：

1. 不可变 RouteHypothesis revision、ProbeRun 双状态、EvidenceBundle、ReviewRecord、RouteDecision、Deviation 为一等合同；
2. host 与 Blender runtime 分进程，host 不导入 `bpy`；
3. 所有外部执行写 JobHandle、日志、哈希和版本化 manifest；
4. 机器只守真实性、可追踪性和状态不变量；
5. 视觉与路线判断由分工明确的 agent/human review 完成；
6. 供应商 Adapter 的 `DONE` 永不等于资产通过；
7. 不维持 v0 兼容层，避免旧抽象继续限制新设计。
8. 老 skills 按 validator / domain knowledge / casebook / obsolete 分类；失败经验默认不编译为 gate。

## 后果

正面：可以在小探针后推翻错误路线；Blender 和云 API 失败可恢复；证据可审计；agent 框架可替换。

代价：无法再用单个布尔 gate 声称“自动验收”；需要目标 owner 对审美和路线承担判断责任；初期 recipe 数量更少。

## 删除边界

本 ADR 只删除被 v1 取代的 `tools/blender-harness` v0 和旧 Hunyuan 命令入口。项目资产、通用 Blender 脚本和现有 AR 参考资料不因本 ADR 被删除。`retarget_bake.py` 在 v1 拥有等价且验证过的 Blender action 前继续保留，因为 retarget 是项目已验证的必要后处理，不属于供应商 Adapter 的 10 类能力。
