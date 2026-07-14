# 执行知识与证据保留

Blender 长程任务中的路线发现是产品资产的一部分，但不同内容需要不同的保存介质。Harness 不把所有经验编译成 gate，也不允许关键发现只存在于聊天记录。

## 四层模型

| 层 | 保存内容 | 当前位置 | 生命周期 |
| --- | --- | --- | --- |
| Run evidence | 请求、JobHandle、脱敏响应、下载物、Blender 文件、渲染、日志 | `.artifacts/routes/<route>/runs/` | 原始现场；大文件、不可发布、默认 gitignored |
| Decision trace | revision、probe、带 SHA256 的 EvidenceBundle、独立 review、decision、deviation | `.artifacts/routes/<route>/` | 当前路线的可审计因果链 |
| Durable cases | 已复核的失败/发现、scope、lesson、scope limit、retirement condition | `docs/knowledge/AR_PRODUCTION_CASEBOOK.md` 与 provider case 文档 | 进入 Git；用于未来提出探针，不自动阻断路线 |
| Executable knowledge | 跨任务稳定且可机械判断的合同 | adapter/schema、tests/fixtures、对应 skill | 进入 Git；必须有正负 fixture，允许随版本退休 |

一次发现可以逐层提升，但不能跳级。Provider `DONE`、一次视觉失败或某个作品的阈值，都不足以直接成为 validator。

## Learning Plane 是投影，不是第五层真相

`.artifacts/learning/v1/` 从上述证据链构造 Context、CapabilitySnapshot、Recipe、Experience、Comparison 和 append-only promotion/retirement event。它的用途是按精确 scope 找回可复现路线、暴露不可比项，并为下一次 shadow probe 推荐候选；源记录或哈希变化时应 fail closed，而不是复制出一份更方便但不可追溯的“真相”。

Learning 记录不得嵌入 API key、Base64 图片、带签名 query 的短期 URL 或未脱敏供应商响应。旧 run 缺少实际费用、有效默认、人工工时或视觉指标时必须保存 `unknown`。跨机器 Evidence Pack 尚未完成，因此本机 promotion 可重建但不是团队级永久授权。

## 每条 durable case 的最小字段

- `date` 与 provider/Blender/API 版本；
- `scope`：资产、输入、目标画面、请求档位；
- `evidence`：route/revision/probe/evidence bundle ID、关键 source SHA256；
- `observation`：实际看到的结果，不混入推断；
- `decision impact`：它改变了哪条路线；
- `lesson`：未来应先问什么或做什么便宜探针；
- `scope limit`：不能从该 case 推出什么；
- `retirement condition`：什么新版本或反例出现时必须重验。

## 本地证据不是永久归档

当前 v1 EvidenceBundle 会重新校验本地文件与 SHA256，但 `.artifacts/` 默认不进入 Git，且 bundle 仍引用本机路径。因此它能防止当前工作区被悄悄覆盖，却不能单独承担跨机器、跨年的证据归档。

在远端 Evidence Pack 上线前：

1. 不删除被 decision/review 引用的 run；
2. 不把带签名 query 的私有 URL、API key 或 credentials 纳入提交；
3. 把关键数值、哈希、适用范围和决定提炼到 Git casebook；
4. 将可复现的 provider envelope 转成脱敏 recorded fixture；
5. 重要大文件由项目对象存储/备份保存，并以 SHA256 对账。

后续应实现 content-addressed Evidence Pack：从已终态 EvidenceBundle 重新验 hash，移除/隔离私有短期 URL，生成带 manifest 的不可变归档并写回外部 URI。该能力完成前，不声称 `.artifacts` 是团队级永久存储。

## 避免知识僵化

- casebook 提供风险线索，不是全局禁令；
- skill 保存领域方法，不保存运行状态；
- validator 只接受可二值判断、跨任务稳定、带正负 fixture 的规则；
- provider/API/Blender 版本变化、目标镜头变化或出现反例时，按 retirement condition 重开 RouteHypothesis。
