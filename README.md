# Blender Harness v1

Blender Harness v1 是一套面向长程 3D 生产的薄作业环境。它不把项目写成一条预设流水线，也不把供应商返回 `DONE`、脚本退出码为 0 或某个固定 case 命中当作资产合格。

它只固定四类可复现事实：

- 路线假设、未知项、停止条件和最便宜的证伪探针；
- Blender 与供应商作业的输入、版本、日志、哈希和输出；
- 执行中新发现的偏差，以及继续、修改、放弃或请求 owner 的决策；
- 少量不容协商的机器不变量，例如文件真实存在、PNG 可解码、任务状态合法、证据齐全。

审美、角色一致性、变形质量、衣服穿模和“最终画面是否成立”由有上下文的评审 agent 与人共同判断，而不是塞进越来越僵硬的程序 gate。

## 快速开始

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

bh doctor --blender /opt/homebrew/bin/blender
bh quicklook model.glb --intent "检查素体轮廓和肩部" --blender /opt/homebrew/bin/blender
# 多对象场景必须显式声明：--subject-mode whole_scene
bh hunyuan capabilities
```

创建一条可被证伪的路线：

```bash
bh route init .artifacts/routes/jiexiaoxian-body \
  --route-id jiexiaoxian-body \
  --goal "可复用、可变形的揭小贤素体" \
  --assumption "多视图候选能保留角色身份" \
  --unknown "肩胯拓扑能否承受动作" \
  --stop-condition "角色身份明显丢失" \
  --alternative "Blender 手工素体与局部重拓扑" \
  --falsification-question "一个肩部极限姿势是否坍塌" \
  --falsification-method "只绑上半身并渲染肩部近景" \
  --budget-seconds 900 \
  --created-by route-scout

bh probe create .artifacts/routes/jiexiaoxian-body \
  --probe-id shoulder-bend-001 \
  --revision-id jiexiaoxian-body-r1 \
  --producer blender-worker \
  --question "肩部是否坍塌" \
  --method "90 度抬臂测试" \
  --expected-evidence shoulder-closeup.png \
  --budget-seconds 300

bh probe finish .artifacts/routes/jiexiaoxian-body \
  --probe-id shoulder-bend-001 \
  --execution-status succeeded \
  --finding refutes \
  --confidence 0.95 \
  --evidence /absolute/path/to/shoulder-closeup.png \
  --summary "腋下拓扑折叠，当前路线不能进入服装阶段"

bh review create .artifacts/routes/jiexiaoxian-body \
  --review-id shoulder-review-001 \
  --revision-id jiexiaoxian-body-r1 \
  --probe-id shoulder-bend-001 \
  --evidence-bundle evidence-<finish输出的id> \
  --reviewer rig-critic \
  --role rig_specialist \
  --recommendation revise \
  --reason "抬臂时腋下折叠，继续做服装会放大返工"

bh route decide .artifacts/routes/jiexiaoxian-body \
  --revision-id jiexiaoxian-body-r1 \
  --probe-id shoulder-bend-001 \
  --verdict revise \
  --premise-broken \
  --reason "自动拓扑无法支撑肩部变形" \
  --review shoulder-review-001 \
  --decided-by animation-director \
  --next-hypothesis "保留头脸，躯干改为手工素体并局部重拓扑"
```

`ProbeRun.execution_status=succeeded` 表示实验执行成功；`finding=refutes` 才表示它成功证伪了路线。两者不能混成一个 failed 状态。路线修订通过 `bh route branch` 创建不可变的新 revision，可同时保留多个候选分支。

## 文档

- [架构与 multi-agent 边界](docs/architecture/HARNESS_V1.md)
- [揭小贤抛金元宝里程碑](docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md)
- [混元 10 类能力 / 19 Actions Adapter](docs/integrations/HUNYUAN.md)
- [ADR-0008：替换 case-heavy Harness v0](docs/adr/0008-harness-v1-clean-replacement.md)
- [旧 skills 迁移矩阵](docs/knowledge/LEGACY_SKILL_MIGRATION.md)
- [真实失败 Casebook](docs/knowledge/AR_PRODUCTION_CASEBOOK.md)

## 验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
RUN_BLENDER_TESTS=1 BLENDER_BIN=/opt/homebrew/bin/blender \
  PYTHONPATH=src python3 -m unittest tests.test_quicklook_blender -v
```
