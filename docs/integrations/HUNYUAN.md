# Hunyuan Adapter

## 完成定义

在 API snapshot `2025-05-13` 下，Adapter 只有覆盖下列 10 类能力、19 个唯一 Action 时才算能力面完整。揭小贤首个里程碑可以只消费多视图生成、AutoRigging 和文生动作，但这不是 Adapter 的完成定义。未来官方新增能力允许扩展 registry；validator 要求当前 required set 不得回退，而不是永远拒绝第 20 个 Action。

| Operation key | 功能 | Submit | Query / Describe |
| --- | --- | --- | --- |
| `geometry.pro` | 专业版生 3D | `SubmitHunyuanTo3DProJob` | `QueryHunyuanTo3DProJob` |
| `geometry.rapid` | 极速版生 3D | `SubmitHunyuanTo3DRapidJob` | `QueryHunyuanTo3DRapidJob` |
| `profile.generate` | 人物画像生 3D | `SubmitProfileTo3DJob` | `DescribeProfileTo3DJob` |
| `rig.auto` | 自动绑骨 | `SubmitAutoRiggingJob` | `DescribeAutoRiggingJob` |
| `motion.text` | 文生动作 | `SubmitHunyuanTo3DMotionJob` | `DescribeHunyuanTo3DMotionJob` |
| `texture.generate` | 纹理生成 | `SubmitTextureTo3DJob` | `DescribeTextureTo3DJob` |
| `topology.reduce` | 减面 | `SubmitReduceFaceJob` | `DescribeReduceFaceJob` |
| `parts.generate` | 部件生成 | `SubmitHunyuan3DPartJob` | `QueryHunyuan3DPartJob` |
| `uv.unwrap` | UV 展开 | `SubmitHunyuanTo3DUVJob` | `DescribeHunyuanTo3DUVJob` |
| `format.convert` | 格式转换 | `Convert3DFormat` | 同步 |

`bh hunyuan capabilities` 在无凭证、无网络时输出该 registry。`tests/fixtures/hunyuan/registry-snapshot.json` 锁定 Action 名称和 Query/Describe 差异。

## JobHandle 语义

`submit` 使用 idempotency key，在调用供应商前先原子创建本地 reservation。同一 jobs 目录中的并发进程不会用同一个 key 重复提交；同 key 不同请求会拒绝。腾讯接口本身没有 provider idempotency token，因此“远端已收到请求、客户端尚未收到或落盘响应”仍是不可消除的 crash window。此时 handle 固定为 `SUBMIT_UNKNOWN`，系统不会自动重试，必须人工根据账单、RequestId 和供应商侧任务记录 reconcile。

JobHandle 分开记录三种状态：

- `submission_status`: `RESERVED / SUBMITTING / SUBMIT_UNKNOWN / SUBMIT_FAILED / SUBMITTED`；
- `provider_status`: `WAIT / RUN / DONE / FAIL / UNKNOWN`；
- `artifact_status`: `NOT_READY / PENDING / FETCHING / FETCH_FAILED / VERIFIED`。

供应商 `DONE` 只表示结果 URL envelope 已返回。下载失败会持久化为 `FETCH_FAILED` 和 `artifact_error`；只有下载、类型检查、魔数检查与 SHA256 全部完成后才是 `VERIFIED`。下载先进入 staging 文件，验证通过后才原子 rename 到最终文件名。

响应历史和 `job.json` 中的 COS URL 会移除 query。下载所需的原始短期 URL 单独保存在权限为 `0600` 的 `result-urls.private.json`；artifact manifest 只保存脱敏 URL。

官方字段名不是统一的：组件与 UV 使用 `File: {Url,Type}`；同步格式转换使用 `File3D: "url"`、`Format`，并返回字符串 `ResultFile3D`。不得用通用 `File3D` 对象猜所有 operation。

## 资产边界

- `geometry.pro` 输出 `raw_geometry_candidate`；
- `rig.auto` 输出 `draft_rigged_character`；
- `motion.text` 输出 `motion_source_skeleton`；
- 其余能力也只输出相应 `candidate`。

所有 manifest 都写入 `provider_done_is_asset_approval: false`。AutoRig 人形应提供 A/T Pose、避免松散衣物和复杂配饰；这属于输入路线约束，不代表输出变形已通过。文生动作不被假定能可靠返回带揭小贤 mesh 的成品，Blender retarget 必须保留。历史上的“API DONE 但 COS 下载失败”必须表现为 `provider_status=DONE + artifact_status=FETCH_FAILED`，不得提升为可 Quicklook 或可发布资产。

拓扑、UV 和纹理没有从揭小贤流程消失：它们是在 body candidate 选定以后，根据真实近景、变形和发布规格决定采用混元能力、Blender 手工处理或混合路线，不能为了“覆盖 API”而无条件串行调用。

## 当前验证等级

registry 和请求合同已有 recorded/synthetic tests；TC3 transport、幂等恢复、下载原子性和 manifest 边界已实现。未配置腾讯凭证的 CI 不声称 live verified；每个 operation 只有在保存脱敏真实响应并经过 Blender Quicklook 后，才可分别升级 maturity。
