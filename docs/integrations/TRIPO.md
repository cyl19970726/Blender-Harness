# Tripo v3 Adapter

## 当前边界

Adapter 公开 2026-07-13 官方文档中的 14 个 operation，但首个纵切只 enable `geometry.multiview`。其余能力显示为 `official_only / submit_enabled=false`，直到每个能力分别有请求验证、脱敏 recorded/live fixture、required output 合同与内容 validator。能力出现在 registry 不等于已经可靠支持。

```bash
bh tripo capabilities
bh tripo credential-status
```

首个 enabled 路线是四张本地 PNG/JPEG → 上传 file token → P1 多视图低模 task → 单次 poll → 主 GLB/preview 整体 fetch。它输出 `raw_geometry_candidate`，manifest 固定写 `provider_done_is_asset_approval: false`。

## 安全凭证

同一台 Mac、同一用户下的 agent 共享 macOS Keychain：

```bash
read -rs 'TRIPO_API_KEY?Tripo API key: '
security add-generic-password -U -a "$USER" -s "blender-harness.tripo" -w "$TRIPO_API_KEY"
unset TRIPO_API_KEY
```

读取优先级为环境变量 `TRIPO_API_KEY` → Keychain service `blender-harness.tripo` → fail closed。没有明文 credentials 文件 fallback。CLI、JobHandle、日志和 manifest 只保存不可逆 credential fingerprint；Keychain 的 file token 与 Key 不是同一事物，file token 也只进入 `0600` private request/upload 文件。

## 作业恢复

Tripo 与 Hunyuan 使用相同三轴语义：

- `submission_status`: `RESERVED / SUBMITTING / SUBMIT_UNKNOWN / SUBMIT_FAILED / SUBMITTED`；
- `provider_status`: `WAIT / RUN / DONE / FAIL / UNKNOWN`；
- `artifact_status`: `NOT_READY / PENDING / FETCHING / FETCH_FAILED / VERIFIED`。

四图上传发生在 `RESERVED` 中，按 view + SHA256 复用已取得的 token；付费 task POST 前才进入 `SUBMITTING`。明确 API reject 进入 `SUBMIT_FAILED`。断线、可能建单的 5xx、2xx 非 JSON、2xx 缺 task_id 等不确定窗口进入 `SUBMIT_UNKNOWN`，重复 submit 不再发 POST。

人工在 Tripo 控制台/账单对账后，可追加 reconciliation record：

```bash
bh tripo reconcile HANDLE --task-id TASK --trace-id TRACE --reason "控制台确认任务存在"
bh tripo reconcile HANDLE --confirmed-not-created --reason "控制台和账单确认未创建"
```

第二种情况把旧 handle 终结为 `SUBMIT_FAILED`；若要重试，创建新的 route probe 与 idempotency key，不修改旧证据。

## 结果与下载

公开 `request.json` 只保存 canonical hash 身份；实际 transport payload 在 `request.private.json`。原始结果 URL 按 generation 追加到 `result-urls.private.json`。公共 response 和 manifest 会递归移除任何 HTTP(S) query/fragment，不依赖字段名是否包含 `url`。

fetch 在网络前要求 operation 的主输出存在；`geometry.multiview` 必须恰有一个主 GLB，preview 可选。下载只允许无 userinfo 的 HTTPS，拒绝 localhost/私网地址和协议降级。整组文件先进入 `fetch-attempts/<attempt>/artifacts`，全部通过格式、GLB version/declared length/chunk bounds、size 和 SHA256 后才发布到 `artifacts/`。失败 attempt 保留，状态为 `provider=DONE + artifact=FETCH_FAILED`。

供应商文档称结果 URL 约五分钟过期，但 API 没有统一、稳定的显式 expiry 字段，因此 JobHandle 不伪造截止时间：只记录 `result_url_observed_at`，provider 明示 expiry 时才写 `result_url_expires_at`。过期只能刷新已存在 task 的结果 envelope，禁止重建付费任务。

## 揭小贤公平探针

同一套新 canonical basemesh 多视图进入：

1. Tripo P1 direct low-poly，首轮 10,000 faces、无纹理；
2. Hunyuan 最接近的低模/四边面能力；
3. 现有权威 FBX，作为现实基线而非新候选输入。

先用 Blender 比较身份、轮廓、精确焊接后壳体、肩/腋/胯/腕/手布线与局部表面。只有静态评审建议继续的候选才进入统一临时 rig 变形探针；UV、纹理、正式 rig、服装和动作不为淘汰候选提前消费。
