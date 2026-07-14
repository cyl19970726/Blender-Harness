# Harness v1：可修改路线，而不是可走完流水线

## 核心判断

Blender 长程任务最危险的不是某一步失败，而是前置路线假设错了却继续积累下游工作。例如完整角色先绑骨，后来才发现身体表面、拓扑和衣服都不成立；或龙头天然下弯、龙身按直线生成，直到拼接时才发现两者根本没有共同接口。

因此 Harness 的基本单位不是 `case -> gate -> pass`，而是：

```text
目标画面
  -> 路线假设（明确假设、未知和停止条件）
  -> 最便宜的证伪探针（不可发布）
  -> 可复现执行（Blender / Hunyuan / 其他工具）
  -> 证据包
  -> 独立 ReviewRecord
  -> Director 决策（继续 / 修改 / 放弃 / 请求 owner）
  -> 新路线或下一个探针
```

## 四个平面

### 1. Control plane

保存目标、不可变 RouteHypothesis revision、ProbeRun、EvidenceBundle、ReviewRecord、RouteDecision 和 Deviation。路线形成可分支 DAG，而不是覆盖一个“当前 JSON”。`execution_status` 描述探针有没有跑成，`finding` 单独描述它支持、反驳还是无法判断假设。路线决策只允许发生在探针进入终态、证据被 hash、独立 reviewer 留下记录之后。

### 2. Execution plane

Host Python 负责进程、超时、目录、原子落盘、哈希、缓存和供应商 JobHandle；`bpy` 只在独立 Blender 进程里执行。供应商、Blender、人工 DCC 都是可替换执行器，不拥有生产真相。

### 3. Evidence plane

每次执行产生版本化 manifest、日志、多视图、几何指标和来源哈希。机器验证证据是不是“真的”，评审者判断证据表达的资产是否“好”。缓存命中也必须复验文件与哈希。

`expected_evidence` 是单个 probe 成功执行时的无条件证据承诺，不是把后续所有可能阶段预先塞进一个列表。若 preflight 的结果决定是否进入 Blender、拓扑或渲染，应拆成两个 probe：前一个先终结、评审和决策，只有获得继续结论才创建后一个。成功 probe 缺少任一预注册证据仍会 fail closed；失败或取消的 probe 只要求保留真实日志/部分证据，并把 `missing_expected_evidence` 写回记录，不能伪造空图片或 `.blend` 补齐列表。

### 4. Learning plane

Learning Plane 是上述三层的旁挂、可重建索引。它只从终态 Probe、可复验 EvidenceBundle、独立 Review 和 Director Decision ingest Experience；把精确 Context、版本化 CapabilitySnapshot、显式参数和步骤 DAG 固化为 scoped Recipe，再做公平性检查、Pareto 比较和最多一个不可发布 challenger 的推荐。它不拥有路线状态、资产审批或发布权限，`unknown` 不参与 dominance，也不被填成 `0`。完整合同见 [LEARNING_PLANE.md](LEARNING_PLANE.md)。

## 机器 gate 只守不变量

适合程序判断：

- 任务状态是否来自有限状态机；
- 输入、产物、manifest、日志是否存在且能解析；
- PNG/GLB/FBX 是否具有正确魔数，文件哈希是否一致；
- 探针是否不可发布、EvidenceBundle 是否真实且未变、路线决策是否引用终态探针和独立 review；
- 前提被击穿时是否错误地继续旧路线；
- Hunyuan `DONE` 是否被错误提升为 Blender 资产 `approved`。

不适合写死成 gate：

- 脸是否精美、角色气质是否像揭小贤；
- 肩、胯、衣摆的变形是否足够自然；
- 镜头节奏和金元宝雨是否有喜庆感；
- 某个失败是否应局部修复，还是应推翻路线。

这些问题由评审 agent 根据目标帧、近景板、动作板和历史决策作出有理由的判断。

## Multi-agent 放置方式

Harness 不需要让多个 agent 对每一个文件投票。它在高信息增益节点引入不同角色：

| 角色 | 介入点 | 产物 |
| --- | --- | --- |
| Director | 目标帧、镜头和发布条件 | Target Brief、不可牺牲项 |
| Route Scout | 新资产或路线被击穿时 | 2–3 条路线假设、最便宜探针 |
| Blender Worker | 路线选定后 | 可复现 run、blend/缓存、证据板 |
| Character/Rig/Cloth Specialist | 相应未知成为当前瓶颈时 | 专项诊断和局部方案 |
| Visual Critic | 每个高代价提交点 | 基于证据的 continue/revise/abandon 建议 |
| Archivist | 决策完成后 | 将发现送往 casebook、知识、validator 或不固化 |

Director 是目标 owner；Scout 与 Specialist 提供选择；Worker 不能 review 或 route 自己的 EvidenceBundle；Critic 不直接改资产；Archivist 不把一次性偶然失败升级为永久 gate。发生分歧时保留各自理由和证据，由 Director 决定，或进入 `ask_owner`。workspace 写操作带排他锁，避免多个 agent 覆盖 revision、probe 或 review。

## 未知项的处理

- KK（已知且知道）：可形成稳定 recipe 或 validator。
- KU（已知自己不知道）：先做预算受限 probe。
- UK（执行后才暴露）：记录 Deviation，立即判断是否击穿前提。
- UU（尚不可描述）：缩小承诺、做可逆实验，不允许通过猜测扩大下游投入。

Deviation 的 `destination` 只创建 knowledge proposal，不会自动发布。Archivist/owner 与 proposer 分离，补充 applicability 和 retirement condition 后才能发布。validator 还必须给出 mechanical test 与正/负 fixture；否则只能留在 domain knowledge 或 casebook。

## 当前实现边界

首个纵切包含：路线 revision DAG、探针双状态、不可变证据、独立 review、知识 proposal/adjudication、真实 Blender Quicklook、Hunyuan/Tripo 可恢复 provider 作业，以及本机 Learning Plane。Quicklook v1 为保证缓存身份正确，暂只接受自包含 GLB；默认只允许单个可见几何，多对象场景必须显式选择 `whole_scene`。预算当前在 route/probe 中记录，runner timeout 会执行；跨 provider 的统一成本账本和跨机器 Evidence Pack 尚未实现，不能声称已经自动控费或拥有团队级永久学习。

它不绑定某个 LLM 供应商；agent 可以由 Codex、人工或以后接入的 orchestrator 承担，只需读写相同证据合同。这避免 Harness 再次被某个 agent 框架锁死。
