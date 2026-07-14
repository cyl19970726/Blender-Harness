# AGENTS.md

本文件是仓库级 Agent 操作合同，适用于整个仓库。若子目录以后出现更具体的 `AGENTS.md`，更深层文件对其目录优先；用户当次明确要求始终优先。

## Mission

本仓库不是固定 Blender 流水线。它的任务是让长程 3D 工作围绕明确最终画面持续暴露错误假设，用最便宜的真实探针决定继续、修改、放弃或请求 owner，并保存可复现证据。

当前产品级验收目标见 `docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md`：先证明揭小贤素体，再证明绑定与动作，再逐件穿衣，最终完成“大揭小贤把金元宝抛向天空并落得满地都是”的镜头。长龙路线当前暂停；除非用户重新启动，不要用龙任务分散这个里程碑。

基础设施的完成定义不是“命令都能跑”，而是它能在真实执行中发现路线错误、保住仍有价值的上游工作，并阻止错误前提继续污染下游。

## Before changing anything

1. 先读 `README.md` 和 `docs/architecture/HARNESS_V1.md`。
2. 若任务属于已有领域，必须读对应 `.agents/skills/<skill>/SKILL.md`；混元任务同时读 `docs/integrations/HUNYUAN.md`，Tripo 任务读 `docs/integrations/TRIPO.md`，揭小贤素体任务再读 canonical entity 与当前 milestone。
3. 检查 `git status --short --branch`，保留用户和其他 Agent 的无关改动。
4. 明确当前目标画面、最危险的路线假设、未知项、停止条件，以及能最快证伪它的 probe。
5. 只有结构稳定、跨任务成立的事实才进入程序 validator；审美 case 和一次性失败留在评审或 casebook。

## Required work loop

```text
Target Brief
  -> 2–3 个可比较的 RouteHypothesis（必要时）
  -> 当前最高信息增益、预算受限且不可发布的 ProbeRun
  -> 真实执行器产生日志、版本、输入/输出 hash
  -> EvidenceBundle
  -> 与 producer 分离的 ReviewRecord
  -> Director: continue / revise / abandon / ask_owner
  -> 分支新 revision，或进入下一个 probe
```

- `execution_status=succeeded` 只表示实验跑成；`finding=refutes` 可以表示它成功证伪路线。不要把两者压成一个 pass/fail。
- 执行中新发现的问题记录为 Deviation。若它击穿前提，旧 revision 不得继续投入下游工作。
- probe 是可逆实验，不是发布资产。不要为了让流程显得完整而提前完成整套拓扑、UV、纹理、rig 或服装。
- Reviewer 必须读取 EvidenceBundle 和目标上下文；producer 不得为自己的证据签发独立 review 或 Director 决策。
- 争议保留各方理由与证据，由 Director 决定；缺少会实质改变路线的 owner 选择时使用 `ask_owner`，不要猜。

## Multi-agent placement

只在工作可独立、边界清楚或需要真正独立判断时并行：

| 角色 | 负责 | 不负责 |
| --- | --- | --- |
| Director | 目标帧、不可牺牲项、路线决策 | 代替 Worker 伪造执行证据 |
| Route Scout | 候选路线、未知项、最便宜探针 | 直接批准资产 |
| Blender Worker | 可复现执行、日志、产物与 EvidenceBundle | 自审与路线拍板 |
| Character / Rig / Cloth Specialist | 当前瓶颈的专项诊断 | 把领域偏好写成全局 gate |
| Visual Critic | 基于证据给出 continue/revise/abandon 建议 | 直接覆盖生产文件 |
| Archivist | 将稳定发现提议到知识、casebook 或 validator | 把一次偶然失败自动升级为规则 |

避免多个 Agent 同时编辑同一文件。委派审计与评审时优先只读；最终写入由一个 owner 整合。

## Source of truth

| 问题 | 权威来源 |
| --- | --- |
| 人类首次进入、成熟度与快速开始 | `README.md` |
| Agent 工作规则 | 本文件 |
| Harness 概念和角色边界 | `docs/architecture/HARNESS_V1.md` |
| 字段与序列化合同 | `schemas/*.schema.json` 与对应 dataclass |
| CLI 真实参数 | `src/blender_harness/cli.py` 和 `bh ... --help` |
| Hunyuan operation / Action | provider registry 与 `docs/integrations/HUNYUAN.md` |
| 当前最终画面 | `docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md` |
| 历史失败及适用范围 | `docs/knowledge/AR_PRODUCTION_CASEBOOK.md` |
| 资产物理位置 | `docs/architecture/ASSET_LAYOUT.md` |
| 领域操作方法 | `.agents/skills/*/SKILL.md` |

文档和实现冲突时，不要静默选一边：用测试或真实 run 确认行为，修正过期一方，并在决策记录中说明。

## Non-negotiable technical boundaries

- Host Python 不导入 `bpy`；Blender 操作必须在独立 Blender 进程中执行，并记录版本、命令、stdout、stderr、超时和退出码。
- Quicklook v1 只接收自包含 GLB；默认 `single_object`，多对象必须显式 `whole_scene`。缓存命中仍需复验 manifest、文件与 SHA256。
- `.artifacts/` 是 gitignored 的作业与证据区，不是发布目录；`/tmp`、聊天附件和短期签名 URL 不能成为权威源。
- Hunyuan provider `DONE` 永不等于 Blender 资产通过。AutoRig 只产生 draft；motion 输出是 source skeleton，必须保留 Blender retarget/bake。
- Tripo `success` 永不等于 Blender 资产通过。只有 operation 标记 `submit_enabled` 才能 live submit；`official_only` registry 不能冒充支持。
- Hunyuan snapshot `2025-05-13` 的 required set 是 10 类能力 / 19 Actions；未来官方新增 Action 可以扩展，不能写“永远只能 19 个”的 gate。
- `SUBMIT_UNKNOWN` 不自动重试；先人工 reconcile，避免重复计费与幽灵任务。
- 不恢复旧 `tools/blender-harness`、固定 Phase/Profile、`gate-status.json`、golden-negative automation 或 case-heavy 总闸。
- 旧 case 可以建议 probe 或 review question；除非同时具备明确适用范围、退役条件、机械测试与正负 fixture，否则不能成为 validator。
- 不把某个 skill 写成第二套状态机。稳定方法留在 skill，具体失败留在 casebook，运行状态只进 `.artifacts`。

## Change discipline

- 改合同：同步 dataclass、schema、CLI/adapter、测试和对应文档。
- 改 provider：使用 JobHandle、幂等 reservation、原子落盘、重试下载、类型/魔数检查、SHA256 与脱敏响应；不得重新引入 `urlretrieve` 式一次性脚本语义。
- 改 Blender runner：必须保留失败 attempt 和部分日志；不得因 Blender 进程退出 0 就假定目标产物存在。
- 改知识：写明 evidence、scope、scope limit；“这个项目曾失败”不等于“所有项目禁止”。
- 改技能：保持短而可执行，frontmatter `name` 与目录一致，`agents/openai.yaml` 的 default prompt 必须显式引用 `$skill-name`。
- 不删除、覆盖或格式化与任务无关的用户改动。破坏性 Git 操作需要用户明确授权。

## Verification

纯 Python 合同：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

真实 Blender 集成（本机路径按实际修改）：

```bash
RUN_BLENDER_TESTS=1 \
BLENDER_BIN=/opt/homebrew/bin/blender \
PYTHONPATH=src \
python3 -m unittest tests.test_quicklook_blender.BlenderQuicklookTest -v
```

提交前至少运行与改动相关的测试和：

```bash
git diff --check
```

没有 live 腾讯凭证时，只能报告 recorded/synthetic 验证；没有真实 Blender run 时，只能报告 host contracts。不要把默认 skip 写成通过。

## Definition of done

一项 Harness 改动只有在以下条件同时满足时完成：

1. 行为边界和非目标被明确；
2. 最小真实路径或稳定机械合同有测试；
3. 失败不会伪装成成功，部分日志与旧 attempt 被保留；
4. README、架构、skill 与代码没有产生新的双重真相；
5. 最终汇报区分“已实现”“已在本地/CI 验证”“尚未 live/产品验证”；
6. 对资产工作，结论引用 EvidenceBundle 与独立 review，而不是命令退出码或供应商状态。
