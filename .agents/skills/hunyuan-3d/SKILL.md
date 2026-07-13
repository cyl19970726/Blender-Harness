---
name: hunyuan-3d
description: 腾讯混元生3D在 Blender Harness v1 中的 provider adapter。涉及混元图/文生3D、多视图、人物画像、AutoRigging、文生动作、纹理、减面、部件、UV、格式转换、10类能力/19 Actions、JobHandle、COS 下载或 Blender retarget 时使用。混元只产 candidate；DONE 永不等于 Blender 资产通过。
---

# Hunyuan 3D Adapter

## 先读

- `docs/integrations/HUNYUAN.md`
- `src/blender_harness/adapters/providers/hunyuan/operations.py`
- `src/blender_harness/adapters/providers/hunyuan/adapter.py`

旧 `scripts/hunyuan3d_gen.py` 和 `scripts/hunyuan_anim.py` 已被统一 Adapter 取代。不要复制旧脚本里的 `urlretrieve`、进程内死循环或临时 URL 处理。`scripts/retarget_bake.py` 暂时保留为 Blender postprocess；它不是混元 provider 能力。

## 完成定义

Adapter 必须保持 10 个 operation、19 个唯一 Action。执行前用：

```bash
bh hunyuan capabilities
```

查看 registry，不凭记忆拼 Action。特别注意：Pro/Rapid/Part 使用 `Query*`；Rig/Motion/Profile/Texture/Reduce/UV 使用 `Describe*`；Convert 同步。

## 调用纪律

```bash
bh hunyuan submit --operation geometry.pro --request request.json --idempotency-key logical-run-001
bh hunyuan poll <handle-id>
bh hunyuan fetch <handle-id>
```

- 每个付费提交必须有稳定 idempotency key；同 key 不得改 request。
- 每次 poll 只做一次请求，让外部 orchestrator 控制节奏与重试。
- 保存 JobHandle、原请求、每次脱敏响应、下载文件、SHA256 与 manifest。
- 状态只允许 WAIT/RUN/DONE/FAIL/UNKNOWN；UNKNOWN 不得猜测。
- URL 有效期有限，DONE 后应及时 fetch；manifest 不保存签名 query。
- 已有 artifact manifest 时 fetch 复验本地哈希，不重复下载或悄悄覆盖。

## 资产角色

- `geometry.pro` → `raw_geometry_candidate`
- `rig.auto` → `draft_rigged_character`
- `motion.text` → `motion_source_skeleton`
- topology/UV/texture/parts/convert 等也只输出对应 candidate

manifest 必须保持 `provider_done_is_asset_approval: false`。

## 项目实跑经验

这些是揭小贤路线的重要证据，但不是对未来官方行为的永久断言：

- AutoRig 人形输入应为干净 A/T Pose，避免松散衣物、道具和复杂配饰；完整穿衣角色不应直接作为首个绑骨输入。
- 项目曾多次观察到文生动作输出为通用动作骨架，不能可靠得到带揭小贤 mesh 的成品。因此把它视为 motion source，并保留 Blender retarget/bake。
- 图生 3D、自动拓扑、UV、纹理、部件拆分都要回 Blender Quicklook/专项 probe；覆盖 capability 不代表应该按顺序全部调用。
- 旧 skill 中“frame-1 neutral、骨骼 DAMP、28→52 骨映射”等属于一次揭小贤 retarget case。复用前先在当前 rig 上做小探针，不升级为通用 validator。

## 验证等级

registry/synthetic fixture、真实腾讯 API、下载产物、Blender 导入与专项视觉评审是不同等级。没有凭证的 CI 只能声明前两层；只有 operation 自己跑过真实作业并留下脱敏 fixture，才能提升其 maturity。不要把一个 operation 的 live 成功外推到其余 9 个。
