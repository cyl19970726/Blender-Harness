# 里程碑：大揭小贤把金元宝抛向天空，落得满地都是

## 它要验证什么

它不是验证 Harness 能否按预设流水线跑完，而是验证 Harness 能否围绕明确最终画面，在执行中发现错误假设、用小实验定位问题，并在不浪费全部下游工作的前提下修改路线。

最终画面由 Director 先定：揭小贤体量巨大、动作喜庆有力；一批金元宝从双手向上喷发，在空中形成清晰弧线，随后落到地面并铺开；镜头能读到脸、手、元宝和落地结果。具体镜头、数量和时长以 target frames 为准，而不是在代码中写死。

## Workstream A：可复用素体

素体的长期实体合同见 [JIEXIAOXIAN_CANONICAL_ENTITY.md](JIEXIAOXIAN_CANONICAL_ENTITY.md)。供应商候选必须证明自己适合作为 canonical high source 或 production cage 的来源，而不是只证明某张静态图能生成 GLB。

首个路线假设可以是“多视图生成保留头脸身份，身体经局部重拓扑后可作为素体”，但必须先用低成本探针证伪：

1. 生成或手工建立 A/T Pose 无衣素体候选；
2. Quicklook 检查正背侧、轮廓、脸、腋下和胯部；
3. 只对肩/胯做临时骨骼和极限姿势，不先完成全套 rig；
4. 若身份成立而关节失败，保留头脸、替换躯干拓扑；若身份也失败，放弃该生成路线。

选定 body candidate 后才处理可发布拓扑、UV 和纹理。近景脸、肩胯变形、移动端预算分别决定手工重拓扑、`topology.reduce`、`uv.unwrap`、`texture.generate` 或混合方案；供应商能力覆盖不是调用顺序。

## Workstream B：骨骼、权重和动作

AutoRigging 只产生 draft。验证顺序从高信息增益的小测试开始：肩、肘、腕、髋、膝、脊柱扭转，再进入完整抛掷。文生动作输出作为 motion source skeleton 导入 Blender，建立骨骼映射、rest pose 修正、root motion 与单位约定，然后 retarget/bake 到揭小贤 rig。

如果手与元宝接触、双手抛掷节奏或重心不成立，优先局部重做关键帧，不把 motion API 的 `DONE` 当作动作完成。

## Workstream C：服装组件

不要再把“完整穿衣角色”直接拿去绑骨。初始可逆拆分建议为 body、上衣/外套、下装、鞋、头部配饰；是否继续细拆由穿模探针决定。

每件衣服选择 match 方法，而不是统一套一个工具：贴身件可共享 armature 并从 body 转移权重；中等厚度衣服先 shrinkwrap/贴合后再做权重和 corrective shape；松散衣摆可用简化 cloth 或手工辅助骨。每加入一件衣服就跑抬臂、下蹲、扭腰和抛掷极值板，发现穿模立即判断局部修复还是修改服装结构。

## Workstream D：金元宝雨

先做一个可读的 hero 元宝并用实例复用。动作与接触阶段可由手部 attachment/control 驱动；离手后可比较三条路线：手工弧线、刚体模拟、程序化轨迹加二次碰撞。用少量元宝 probe 验证剪影、碰撞稳定和落地构图，再扩大数量并缓存。最终元宝应是实例或轻量代理，避免每一枚都成为独立高模。

## 关键路线决策点

- 素体候选的身份和关节拓扑是否值得继续；
- AutoRig 是否保留，还是替换为 Blender rig；
- 服装是共享权重、辅助骨还是 cloth；
- 动作源能否 retarget，哪些段落需要手工关键帧；
- 元宝雨采用可控轨迹还是物理模拟；
- 当前问题是局部修复，还是已经击穿路线前提。

每个决策都必须引用已完成 probe 的不可变 EvidenceBundle 和独立 ReviewRecord。最终验收以 target-frame 对比、完整镜头、近景变形/穿模板和可复现 run 为准，不以流程节点全绿为准。
