# Tripo v3 snapshot（2026-07-13）

权威入口：

- API quick start: <https://developers.tripo3d.ai/en/docs/quick-start>
- multi-view to model: <https://developers.tripo3d.ai/en/docs/generation-multiview-to-model>
- file upload: <https://developers.tripo3d.ai/en/docs/files>
- task query: <https://developers.tripo3d.ai/en/docs/task-query>
- Smart Retopology: <https://developers.tripo3d.ai/en/docs/mesh-decimate>
- pricing: <https://developers.tripo3d.ai/en/pricing>

Base URL 为 `https://openapi.tripo3d.ai/v3`，Bearer API key。异步 submit 返回 `data.task_id`，`GET /tasks/{task_id}` 返回 `queued/running/success/failed/cancelled/banned` 等状态、`output` 与实际 `credits_consumed`。结果 URL 是短期传输地址，应在成功后立即私有化保存并下载。

当前 registry 包含 14 个 operation；只有 `geometry.multiview` 已 enabled。其他 endpoint 仅用于能力发现：text/image/multiview generation、image-to-multiview/edit-multiview、model import/texture/convert、mesh decimate/segment/complete、rig-check/rig/retarget。

P1 模型名在官方页面存在不一致：quick-start 使用 `P1-20260311`，部分专页/示例可能出现别名。live probe 必须记录实际 request/response；遇到明确 4xx 时记录 deviation 后修订，不把某个页面的字符串编译成永久 validator。

多视图顺序也有过示例不一致。Harness 当前采用 `[front,left,back,right]`，因为它与参数表和通用视图语义一致；任何实际 API 拒绝或明显左右错位都属于可证伪路线发现。

首个 P1 无纹理多视图 probe 预算按官方价格页预估约 40 credits；最终账务只认任务响应中的 `credits_consumed`。不得为了覆盖能力面在淘汰候选上继续消费 retopo、rig、texture 或 animation。
