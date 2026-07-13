# 旧 skills 与失败经验迁移矩阵

本文件记录 Harness v0 清理后，旧知识进入 v1 的去向。它不是兼容层，也不要求恢复已经删除的目录、脚本或 gate。迁移原则是：保留能帮助当前决策的领域判断和真实失败证据，退役把偶然 case 写成永久流程的做法。

## 迁移判据

| 旧内容类型 | v1 去向 | 进入条件 |
| --- | --- | --- |
| 跨任务稳定的机械事实 | schema / validator / runner test | 有机械测试；需要时有正负 fixture |
| 领域内稳定的制作方法 | 对应 `.agents/skills/*/SKILL.md` | 写清适用场景，不成为第二套状态机 |
| 一次真实失败及其证据 | `AR_PRODUCTION_CASEBOOK.md` | 有 scope、evidence、lesson、scope limit |
| 当前路线选择与发现 | `.artifacts/routes/...` | 由 revision、probe、evidence、review、decision 保存 |
| 过时路径、固定 gate、重复状态镜像 | 删除 | 不保留兼容入口 |

## 迁移结果

| 旧主题 | 保留的经验 | v1 位置 | 明确退役的部分 |
| --- | --- | --- | --- |
| Blender Harness / Advance | 真实 headless 执行、证据优先、失败留痕、先小探针 | `blender-harness` skill、`HARNESS_V1.md`、runner/tests | 固定 Phase/Profile、通用 Gate 表、`gate-status.json`、golden-negative 总闸 |
| Hunyuan 一次性脚本 | 生成、AutoRig、motion、retarget 的实跑发现；COS 下载失败经验 | `hunyuan-3d` skill、统一 provider adapter、Hunyuan 文档与 fixtures | `urlretrieve`、进程内无限 poll、临时 URL 当资产、provider `DONE` 当批准 |
| 东方长龙 | visual source 与 production control 分离；头颈身接口必须先探针；近镜连续性优先 | `jygc-dragon-rig-pipeline` skill、casebook | 假定分段一定可拼、先做完所有模块再测连接、固定 rig 流水线 |
| 真实景点 AR | photo-match、固定效果相机、effect/live composite、来源边界 | `jygc-spot-animation` skill、资产文档、casebook | 固定六拍/G0 套件、全帧重绘直接当实时效果、裸层自我批准 |
| 卡面 / 冰箱贴 AR | 商品专属性、边缘 owner、2D/2.5D/3D/hybrid 路线比较 | `jygc-magnet-animation` skill、casebook | 固定七拍、用 alpha 指标代替成片判断、同一模板套所有 SKU |
| 资产整理与拉片 | provenance、manifest、参考/触发/美术分离、参考卡必须服务产品决策 | `jygc-ar-assets`、`jygc-ar-lapian` skills、`ASSET_LAYOUT.md` | 只按扩展名搬文件、把 `/tmp` 或聊天附件当权威源、无结论截图堆积 |
| 历史 issue / case | 能提醒下一次路线风险的问题模式 | `AR_PRODUCTION_CASEBOOK.md`，按需被 reviewer 引用 | 自动把每个 issue 编译成程序 case 或全项目禁令 |

## 旧实跑脚本的边界

`scripts/` 中仍可能存在一次性制作或 Blender postprocess 脚本。它们是迁移来源或人工工具，不自动获得稳定 Adapter 身份。只有在补齐输入合同、版本记录、超时、幂等、原子落盘、哈希、失败恢复和测试后，能力才能进入 Harness 执行面。

`scripts/retarget_bake.py` 当前仍可作为 Blender postprocess 参考；它不属于混元 provider 能力。旧 `hunyuan3d_gen.py` 与 `hunyuan_anim.py` 的职责已经由统一 Adapter 接管，不应恢复为正式入口。

`jygc-ar-assets` 与 `jygc-ar-lapian` 已重新定界：资产 manifest 与触发图台账是从产品仓保留的历史快照，不能驱动本仓文件操作；拉片库只保存被接受的轻量决策卡，原始研究落在 `.artifacts`。任何微信小程序资产移动必须回到真实产品工作区并重新核验 live manifest。

## 如何处理新发现

执行中先把发现记录为 Deviation，不直接修改全局规则：

1. 只解释这次失败：留在当前路线记录；
2. 对同领域以后有帮助：提出 domain knowledge 或 skill 更新；
3. 是有范围的真实事故：进入 casebook；
4. 能机械判断、跨任务稳定且有 fixture：才进入 validator；
5. 证据不足或适用范围不清：保留为 proposal，不能发布。

知识必须允许退休。供应商接口变化、Blender 版本变化、目标镜头变化或新的反例出现时，应修改 applicability 或 retirement condition，而不是让旧规则永久增长。
