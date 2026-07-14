# 揭小贤 canonical character entity

## 目的

新素体不是一次渲染的“裸体角色”，而是揭小贤未来换衣、换动作、做近景和移动端 LOD 的稳定母体。它必须既保留 IP 身份，也允许头脸、身体 cage、头发、眼牙、服装与配饰按明确 ownership 独立迭代。

## 实体形态

- 采用轻微 A Pose：肩不过度水平拉伸，手臂离体，手掌朝前或轻微内旋，五指留出可读间隙；双腿分开、脚底同地线、脚尖向前。
- body deformation cage 是连续、封闭、可变形的主体；不把袍服、袖口、腰带、鞋、屋顶帽、肩狮、流苏或一次性关节缝烘进身体。
- 头脸保留揭小贤的大棕眼、圆幼脸、暖和聪明的表情、头身比与发际轮廓。头发作为可替换 cap/shell，不焊死到颈肩。
- 眼球、牙/口腔、头发、服装和硬配饰是独立 owner。身体隐藏面可以在具体服装资产中用 mask 管理，但 canonical body 不因某套衣服被永久切坏。
- 肩环、腋下、肘、腕、髋、腹股沟、膝和踝保留面环与体积，优先服务“双手向上抛元宝”的举臂、抓握、释放和落地缓冲。

## 交付层级

```text
identity references
  -> canonical high source（形体/脸部细节）
  -> production deformation cage（稳定四边面与 UV）
  -> rig interface（单位、朝向、骨架/服装基准）
  -> LOD0 / LOD1 / LOD2 derivatives
  -> outfit components and motion clips
```

不能用一个 provider GLB 同时冒充所有层。生成候选可以成为 high source 或 cage 的局部来源；只有经过 Blender 拓扑与变形证据后才确定角色。

## 稳定接口

- Blender 米制单位，角色朝向与 root/up axis 在 asset manifest 固定；变更需要新 revision。
- 固定头顶、下巴、肩峰、肘、腕、髂嵴、膝、踝、脚底等 landmark，供多视图对齐、骨架、服装和 LOD 比较。
- production cage 目标是以变形和移动端预算为依据的四边面主体，不把“quad 比例高”本身当质量证明。
- UV、材质槽、vertex groups、shape keys 和 corrective 的命名在候选选定后冻结；生成阶段不为了流程完整提前冻结错误 topology。
- 服装按贴身、中厚、松散和刚性配饰分别选择权重转移、shrinkwrap/corrective、辅助骨/cloth、刚性 parent，不要求统一 match 方法。

## 首个素体多视图合同

新图由权威 P2B 只约束脸、发型、IP 气质和品牌识别；现有正/左/背正交渲染只约束身体尺度、体积和相机一致性。冲突时脸跟 P2B，身体比例跟真实正交体块；两者的服装、旧脸洞、简化手、表面缺陷一律不继承。

输出 front/left/back/right 四张同尺度、同姿势、同地线、接近正交的独立图。白底、无阴影、无道具、无标签、无服装/配饰；使用平滑、非解剖化、无性征的玩具素体表面。它们首先是不可发布 probe 输入。

## 停止条件

出现任一情况，生成路线不能继续到正式 rig：

- 脸或比例读成通用 Q 版小孩，而不是揭小贤；
- 四视图在头宽、肩宽、手脚位置或地线明显不一致；
- 袍服、连体衣边、关节环、鞋或配饰被烘进 body；
- 手指融合、手掌方向不明确，无法验证抓握/释放；
- 肩腋或髋裆需要整体重铺才可能变形，且不优于修复现有 FBX；
- 只在静态中好看，统一举臂/屈髋探针不成立。

候选失败不意味着必须放弃它的全部信息：身份成立而 body 失败时可以只保留头脸 high source；身体 cage 成立而头手失败时可以做局部替换。任何 salvage 都要成为新 revision，而不是静默覆盖原路线。
