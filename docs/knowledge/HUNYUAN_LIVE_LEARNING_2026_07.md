# Hunyuan live 经验投影（2026-07）

## 范围

本文记录 2026-07-13 揭小贤五次 Hunyuan live submit 的事实层，供 Learning Plane 构造 CapabilitySnapshot、ExperienceRecord 和后续 probe。它不是供应商排名，也不把旧 Review 自动转换成统一质量分。

共同 API version 为 `2025-05-13`。运行时 Adapter commit、服务端 topology 模型 revision、有效默认参数、人工修复分钟、废弃下游工作和上游保留率均未完整记录，必须保持 unknown。

这五次历史 run 当前只完成了可提交的事实审计，尚未伪装成可 promotion 的 `ExperienceRecord`：旧记录缺少足以重建的 CapabilitySnapshot/有效默认，且本机 EvidenceBundle 还不是跨机器 Evidence Pack。后续可以把它们 ingest 为 disputed/unknown 经验或重跑 bounded shadow；在补齐前，本文是迁移来源，不是 champion 依据。

## 已执行作业

| Run / operation | 显式参数 | 事实产物 | 费用 | 路线影响 |
| --- | --- | --- | --- | --- |
| `hunyuan-neutral-basemesh-001` / `geometry.pro` | Model 3.1、Normal、FaceCount 30000、PBR false、正面+5 辅助视图 | GLB SHA `1a7149d2eda6737a91968ae938610d6188d6a5fa6f941c2c5ace80271e9721bf`；30k tris；GLB 20,004v | 返回 40 credits | 执行成功、`finding=refutes`；身份 donor 有价值，但随机三角拓扑与肩颈/手部问题击穿直接素体路线 |
| `hunyuan-smart-topology-lowquad-002` / `topology.reduce` | quadrilateral、FaceLevel low | OBJ SHA `42ec4647893890fa8b1ee2231bf9c4ec4f9720404dc409a2123b1b9adeb2775c`；4,945v / 5,198f；4,669 quads；54 boundary、17 multi-face edges | 实际返回 unknown | 只支持同输入做一次 high retry，不批准资产 |
| `hunyuan-smart-topology-highquad-003` / `topology.reduce` | quadrilateral、FaceLevel high | OBJ SHA `4077e0ec40f0f74cae271ffd0bb3ab5684424d94f065e4f42354764333092573`；6,994v / 7,421f；6,562 quads；8 boundary、1 multi-face edge | 实际返回 unknown | 机械指标优于 low，但人物关键区域和尺度漂移仍使路线被放弃 |
| `hunyuan-pro30-lowpoly-source002-001` / `geometry.pro` | Model 3.0、LowPoly、quadrilateral、PBR false、四视图 | primary OBJ SHA `7f73b6a9c89821fba0e6676126f3b2d76f98376447ed122ca671d852531f8942`；6,763v / 7,773f；73.9997% quads；闭合 manifold；19 个非相邻三角交叠 | 返回 35 credits | 保留身份/比例/A-pose，可作 shape donor；只继续不可发布最小变形 probe，不是 production cage |
| `jxx-hunyuan-highquad-shoulder-001` / `topology.reduce` | quadrilateral、FaceLevel high | OBJ SHA `cfd211c435e282d5006ad8c5ba7e8c71830f83d233ded40d26b79da5492825b4`；7,469v / 7,921f；88.5999% quads；6 boundary、7 multi-face、3 winding conflict、36 triangle intersections | 实际返回 unknown | 供应商执行成功、`finding=refutes`；停止 deform/rig/UV/texture/clothing，转向 Blender 局部 body donor 与肩部重拓扑 |

“实际返回 unknown”不能替换成官方标价 50 credits。官方价格可以进入 CapabilitySnapshot 的 `documented_pricing`，不能进入 OutcomeVector 的实际成本 observation。

## 传输与证据偏差

- Normal run 是 Adapter 修复前的旧 manifest；供应商逻辑 `Type=OBJ` 实际是 ZIP bundle。旧证据保留 deviation，不能原地追认为裸 OBJ。
- Low/High topology 的共同输入是 Normal GLB SHA `1a7149…721bf`；旧请求没有显式保存内容 SHA，该 lineage 属于 `hash_provenance=derived`。
- LowPoly 的 ZIP container SHA 与 unpacked primary OBJ SHA 不同。几何比较使用 primary OBJ，容器 SHA 只证明 transport 包未变。
- Highquad 的前三个 Blender attempt 属于 evaluator/runner 失败，第四次才成功生成证据；它们不能记成 Hunyuan provider 失败。
- R12 对交叠区域的早期语义定位被 R13 新证据修正；机械数值保留，旧语义判断标记 superseded，不升级为 validator。

## ComparisonSet 边界

当前唯一接近单变量公平 A/B 的集合是：

```text
Normal GLB 1a7149d2eda6737a91968ae938610d6188d6a5fa6f941c2c5ace80271e9721bf
  -> topology.reduce / quadrilateral / low
  -> topology.reduce / quadrilateral / high
```

比较前仍需统一 scale/center，并把实际费用、人工分钟、变形质量保留为 unknown。LowPoly 原始输出与 `LowPoly → high topology` 是路线增量比较，不是独立供应商 A/B。Normal 3.1 六视图与 LowPoly 3.0 四视图同时改变输入、模型、模式和目标，不能直接得出“Normal vs LowPoly 谁更好”。Tripo 当前没有成功几何产物，也不能比较几何质量。

## 重新验证条件

- Hunyuan model、Action schema、默认值、价格或 transport 迁移；
- Adapter 行为或 manifest 合同改变；
- target brief、相机距离、资产 stage 或 desired output role 改变；
- 新证据提供 topology 实际账单、统一变形板或人工修复工时；
- 相同输入的 Tripo/Rodin/Blender challenger 产生完整 EvidenceBundle。

这些触发条件应产生新的 CapabilitySnapshot/Recipe revision 和 bounded shadow probe，不修改旧 run 来制造“从来正确”的历史。
