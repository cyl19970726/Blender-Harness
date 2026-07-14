---
name: tripo-3d
description: Tripo v3 在 Blender Harness 中的可恢复 provider adapter。用于 Tripo P1 低模、多视图生 3D、Smart Retopology、文件上传、task poll/fetch、AutoRig、retarget、与混元候选对比，或处理 Keychain、短期 URL、SUBMIT_UNKNOWN 和 provider DONE 不等于资产通过等边界。
---

# Tripo 3D Adapter

## 先读

- `README.md`
- `docs/architecture/HARNESS_V1.md`
- `docs/integrations/TRIPO.md`
- 当前任务若是揭小贤，再读 `docs/milestones/JIEXIAOXIAN_CANONICAL_ENTITY.md` 和 `docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md`
- 需要核对 endpoint、模型版本或成熟度时读 `references/API_V3_SNAPSHOT.md`

Tripo 是候选生产者，不是资产审批者。`success`、`provider_status=DONE`、GLB 可解析或 P1 标称 clean topology 都不能替代 Blender 多视图、拓扑、身份和变形评审。

## 凭证

优先读取 `TRIPO_API_KEY`，否则读取 macOS Keychain service `blender-harness.tripo`。禁止把 Key 写进仓库、`.env`、request、fixture、日志、manifest 或命令历史。`bh tripo credential-status` 只输出来源和 fingerprint。

## 执行合同

```bash
bh tripo capabilities
bh tripo credential-status
bh tripo submit \
  --operation geometry.multiview \
  --request request.json \
  --idempotency-key logical-probe-id
bh tripo poll HANDLE
bh tripo fetch HANDLE
```

首个 enabled operation 只有 `geometry.multiview`。registry 中的其余官方能力为 `official_only`，在具备 recorded/live fixture、request validator、required-output extractor 与内容 validator 前不得提交。

本地多视图 request 使用严格顺序：

```json
{
  "inputs": [
    {"view": "front", "path": "/absolute/front.png"},
    {"view": "left", "path": "/absolute/left.png"},
    {"view": "back", "path": "/absolute/back.png"},
    {"view": "right", "path": "/absolute/right.png"}
  ],
  "model": "P1-20260311",
  "model_seed": 20260713,
  "face_limit": 10000,
  "texture": false,
  "pbr": false
}
```

Adapter 在付费 POST 前原子 reservation，按输入 SHA 恢复上传，file token 和原始结果 URL 只写 `0600` private files。每次 `poll` 只请求一次；外部 orchestrator 决定等待频率。下载整个结果集先进入 attempt staging；必须存在主 GLB，并通过完整 GLB header/declared-length/chunk 与 SHA256 检查后才能整体发布。

任何可能已经创建远端任务但没有可靠 `task_id` 的窗口进入 `SUBMIT_UNKNOWN`，永不自动重提。只有通过供应商控制台/账单取得明确证据后，才使用：

```bash
bh tripo reconcile HANDLE --task-id TASK --trace-id TRACE --reason "..."
bh tripo reconcile HANDLE --confirmed-not-created --reason "..."
```

## 揭小贤对比

同一组新素体多视图、同一几何意图和接近的面预算比较 Tripo 与 Hunyuan；旧 FBX 是第三基线。先比较身份、轮廓、壳体、肩/腋/胯/腕布线和 canonical entity 适配性。静态候选被淘汰时停止，不提前调用 rig、UV、纹理或 retarget。

P1 输出属于 `raw_geometry_candidate`。若值得继续，下一探针才做统一临时 rig 与抛元宝所需的举臂/抓握/释放极值，而不是把 Tripo AutoRig 当作完成。
