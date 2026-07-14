# Learning Plane：学习 scoped recipe，不做供应商排行榜

## 目标

Learning Plane 回答一个受范围约束的问题：

> 对当前目标画面、资产族、资产阶段、输出角色、平台、预算和证据协议，哪个版本化 Recipe 值得作为 champion，哪个 challenger 值得做下一次不可发布 shadow probe？

它不会训练一个“万能质量分”，不会把供应商 `DONE` 变成质量奖励，也不会替 Director 或 owner 发布资产。它是现有 `RouteHypothesis → ProbeRun → EvidenceBundle → ReviewRecord → RouteDecision` 的旁挂索引，不是第二套路线状态机。

## 数据流

```text
官方文档/真实执行
  -> ToolCapabilitySnapshot
  -> RouteRecipe（工具版本 + 显式参数 + DAG + 停止条件）

终态 Probe + EvidenceBundle + 独立 Review + Director Decision
  -> OutcomeVector（observed / unknown / not_applicable）
  -> ExperienceRecord
  -> ComparisonSet（公平性 + Pareto，不做总分）
  -> RecipeRecommendation（scoped champion + 最多一个 shadow challenger）
  -> RecipePromotion append-only event
```

供应商状态、下载状态和质量结论始终分开。`execution_status=succeeded + finding=refutes` 是有价值的经验：实验成功证伪了路线。

## 核心合同

### ContextContract

Context 固定 target brief 引用与 SHA256、asset family、asset stage、desired output role、platform、hard constraints、evaluation protocol、budget envelope 和本 scope 的 objectives。人物、建筑、龙不共用一套全局质量 gate。Context 内容不同就形成不同 scope fingerprint，旧 champion 不会跨 scope 偷渡。

### ToolCapabilitySnapshot

Snapshot 保存 provider/tool、transport、operation、模型/API/Adapter 版本、官方文档、参数合同、价格、验证等级、冲突和重验条件。会改变成本或下游工作的参数必须声明 `requires_resolution=true`；Recipe 要为它保存值和来源：`explicit`、`provider_default` 或 `derived`。

历史 run 的有效默认若无法重建，应显式保持 unknown 并使 Snapshot/Recipe 保持 disputed；不能用今天的文档默认值回填过去。

### RouteRecipe

Recipe 是产物依赖 DAG，不负责自动做 `continue/revise/abandon`。每一步引用 CapabilitySnapshot，保存 operation、输入/输出 binding、全部高影响参数、参数来源、预算和证据义务。重复 step、悬空依赖和循环依赖会 fail closed。

### OutcomeVector

每个 Context objective 都必须出现，状态只能是：

- `observed`：有数值和证据引用；
- `unknown`：有原因、`value=null`；
- `not_applicable`：有原因、`value=null`。

缺失 objective 会在 ingest 时补成 `unknown`，永远不会补成 `0`。供应商没有返回拓扑实际积分时，官方标价不能冒充实际消耗；自然语言 Review 也不会被自动翻译为统一美术分。

### ExperienceRecord

Experience 必须从终态 Probe、可复验 EvidenceBundle、独立 Review 和 Director Decision ingest。它保存 route lineage 的记录 SHA、实际输入角色/SHA、执行模式、供应商/下载状态和 Outcome 引用。输入 SHA 若是推导而非原请求显式保存，必须写 `hash_provenance=derived` 和 derivation。

执行模式为 `explore / shadow / production`。Explore 与 shadow 固定 `non_publishable`；production 也只有 `external_authority_required`，Learning Plane 自己没有资产发布权限。

### ComparisonSet

`single_step_same_input` 必须有相同输入 role→SHA；`end_to_end_same_target` 至少要求完全相同 Context。机械不公平会保存为 `incomparable`，不会产生优劣排序。

可比较候选只做 Pareto dominance。任一参与维度为 unknown 时，该维度不能用于 dominance；系统保留 uncertainty，不把美术、成本和返工压成单一总分。

### Recommendation、Promotion 与 Freshness

Recommendation 是只读投影：精确 scope、最新 Snapshot、ComparisonSet 和当前 append-only event 共同决定一个 champion 和最多一个 challenger。Challenger 固定为 `shadow + non_publishable + may_use_for_production=false`。

Promotion 需要可比较 ComparisonSet、fresh recipe、前瞻 shadow Experience、独立 promotion review 和 Director/owner 决策。若 challenger 没有严格支配当前 champion，只有 owner 可以显式接受 trade-off。`expected_current` 提供乐观并发保护。

Snapshot 发生模型、API、Adapter、参数合同、能力面或价格变化后，依赖旧 Snapshot 的 recipe 会变 stale/disputed。系统不会自动迁移到新默认值，而是要求新的 bounded canary。

## CLI

Learning 命令全部离线，不调用 Blender 或供应商：

```bash
bh learn freshness --snapshot capability.json
bh learn freshness --snapshot capability.json --record --actor archivist --reason "official schema observed"

bh learn ingest \
  --route-workspace .artifacts/routes/<route> \
  --probe-id <probe> --decision-id <decision> \
  --context context.json --recipe recipe.json --outcome outcome.json \
  --inputs inputs.json --mode explore --ingested-by archivist

bh learn compare --spec comparison.json
bh learn recommend --context context.json --generated-by director
bh learn promote --context context.json --candidate recipe@r1 \
  --comparison comparison-id --review promotion-review.json \
  --promoted-by director --role director --reason "..." --expected-current none
bh learn retire --context context.json --expected-current promotion-id \
  --retired-by director --role director --reason "provider snapshot changed"
```

默认 store 是 `.artifacts/learning/v1/`。实体不可变；scope event append-only，不维护容易分裂的 `champion.json` 指针。

## 当前边界

这是本机 Learning MVP，不是团队级永久记忆：

- EvidenceBundle 仍引用绝对本机路径；
- `.artifacts/` 默认 gitignored；
- actor id 是字符串，不是远程身份或不可抵赖签名；
- promotion 只表示 scoped recipe champion，不代表资产发布批准；
- 推荐器是透明的 case retrieval + freshness + Pareto，不是强化学习。

跨机器持续学习需要 content-addressed Evidence Pack：重新验证 EvidenceBundle SHA，隔离私有 URL，归档大文件到批准的对象存储，并保存稳定 URI、manifest SHA 和回滚版本。该能力完成前，不声称项目已经拥有永久、自主、跨机器的“自学习”。
