# 揭阳古城 AR / Blender 生产 Casebook

本文件保存具体失败及其适用边界。它不是 gate 清单，也不自动约束新路线。使用某条记录前，先核对 `scope` 是否与当前目标、资产和输出合同相同；若不同，只把它当作提出探针的线索。

只有跨路线稳定、可二值机检、且正反例充分的结论，才应另行提升为 validator。领域判断留在对应 skill；一次性异常留在这里。

## BH-001 · Gate D v01 的 proxy 盖屏

- **date**: 2026-06-30
- **scope**: 天坛语法磁贴；长龙承担近镜擦除；121 帧 reduced candidate。
- **evidence**: `longling12/jieyanggucheng#130`、`#131`；历史 fixture `gate-d-v01-negative`；重点帧 f072/f116/f117。
- **observation**: runtime、SBS 和遮挡覆盖均能工作，但高覆盖帧读成低模球/管，而不是有机龙。阶段性 proxy 被带入了产品候选。
- **lesson**: provider/technical success 不能批准可见资产；当某资产将占据近镜或大面积画面时，先用真实 closeup 探针验证它。proxy/probe 输出必须保持不可发布，直到有明确 RouteDecision。
- **scope limit**: 不推出“所有镜头必须低覆盖”，也不推出固定覆盖阈值；满屏可以是正确叙事事件。

## BH-002 · P11–P40 局部 proof 通过，P41 推翻整条龙路线

- **date**: 2026-07-06—2026-07-07
- **scope**: 进贤门长龙，模块化头/颈/身/尾，后续 rig、motion、source-pass、alpha/SBS proof。
- **evidence**: `longling12/jieyanggucheng#147`，尤其 P11、P15、P40 与 P41 asset route reset comments。
- **observation**: 多个局部 proof 的 checker 为 accepted，P40 甚至证明了 alpha/SBS 像素一致；最终 closeup 仍显示头、颈、身体是拼接模块。P41 记录 `review_scope_asked_wrong_question` 与 `proof_only_acceptance_leaked_into_final_asset_route`。
- **lesson**: 局部探针只能回答声明的问题，不能继承为产品美术成立；每个 RouteDecision 必须回看目标画面和尚未验证的前提。长龙 source 路线要尽早问“无 helper 的头颈身是否是一条连续生物”。
- **scope limit**: 不否定模块化控制资产、source-pass 或 SBS 技术；否定的是把局部技术 proof 当作最终可见美术证据。

## BH-003 · 一次性脚本与 audit 语义分叉

- **date**: 2026-07-02 复盘
- **scope**: 早期多条 Blender/AR 探索线。
- **evidence**: `jieyanggucheng#131` 历史审计：42+ 个 per-artifact 脚本，另有互相矛盾的 coverage audit。
- **observation**: 每个候选重新发明脚本和阈值，无法形成稳定行动空间；同名指标在不同作品里含义相反。
- **lesson**: 可复用 action 应参数化并记录版本、命令、输入和输出；指标必须说明它代理的风险和适用场景。不要把作品特定阈值提升为全局 machine invariant。
- **scope limit**: 一次性诊断脚本仍可用于探索，只要明确不可复用且不伪装成生产接口。

## BH-004 · 状态镜像漂移与验证器分叉

- **date**: 2026-07-02 复盘
- **scope**: Gate D 候选状态、Blender 验证渲染与最终 runtime 渲染。
- **evidence**: `jieyanggucheng#131`；历史记录提及状态在 6–8 处手工镜像、`scene_verify` 2× scale、绝对赋值覆盖 GLB 嵌套 scale。
- **observation**: 文档状态与机器状态漂移；验证器和最终渲染使用不同 scale/相机语义，连续多轮判断建立在错误画面上。
- **lesson**: 控制状态只保留一个机器可读来源；quicklook/final 必须记录并对账相机、分辨率、色彩管理、transform 与 source hash。
- **scope limit**: 具体 2× scale 是历史 bug，不应成为永久特例。

## BH-005 · 长版本 churn 与定向诊断板

- **date**: 2026-06-25—2026-07-04
- **scope**: 功夫茶 2D 路线、real-model 路线、进贤门《叩城》多轮合成。
- **evidence**: `jieyanggucheng#59`、`#140`；历史总结“2D 22 版 / real-model 9 版”，touchdown 诊断板一次排除多个相邻版本。
- **observation**: 没有显式假设和停止条件时，版本号增长不等于信息增长；针对单一未知的诊断板比继续做完整候选更有效。
- **lesson**: RouteHypothesis 应写预算、未知和停止条件；每次重跑声明预期改变。触发停止的次数由路线风险和成本决定，不固定为“两败”。
- **scope limit**: 不要求所有失败都停工或请求 owner；低成本、可逆探针可继续。

## HY-001 · Hunyuan 文生动作不返回目标角色 mesh

- **date**: 2026-06
- **scope**: 产品 1804 API；揭小贤；三次 `RetargetFile`/`EnableMesh` 实跑。
- **evidence**: 旧 `.agents/skills/hunyuan-3d` 的实跑记录；当前权威边界见 `docs/integrations/HUNYUAN.md`。
- **observation**: 三次输出均为约 52 骨、无角色 mesh 的动作源 FBX；目标角色 rig 是另一份约 28 骨资产。
- **lesson**: `motion.text` 输出按 `motion_source_skeleton` 管理；保留 Blender retarget/bake 路线，不把 provider `DONE` 当成 animated character。
- **scope limit**: 这是带日期的 provider observation，未来 API 版本可通过新 live probe 推翻，不能写成永恒事实。

## HY-002 · 临时 URL、下载中断与 raw 未落地

- **date**: 2026-07-02
- **scope**: Hunyuan COS 下载；`JXM_DRAGON_LIGHT_BODY_V01`。
- **evidence**: 旧 `hunyuan-3d` 项目状态，记录 `download_status=blocked_by_local_cos_tls_timeout` 与 `urlretrieve` 的 `RemoteDisconnected`。
- **observation**: Job 已 DONE 且有预览 URL，但 raw GLB 没有可靠落地，仍被口头描述为资产入场。
- **lesson**: 下载使用可恢复 JobHandle、重试、`.part`、原子 rename、magic 与 SHA256；签名 URL 不作为长期资产地址。
- **scope limit**: `curl` 是当时有效 workaround，不是唯一永久实现。

## HY-003 · 轴倾斜、面数与材质档位样本

- **date**: 2026-06
- **scope**: 揭小贤 Pro 3.1 多视图样本；小尺寸 AR 角色。
- **evidence**: 旧 `hunyuan-3d`：单图样本约 10° 倾斜；30k/无 PBR/1024 与 150k/PBR 的体积和远景观感对比。
- **observation**: 多视图降低了轴倾斜风险；小屏角色在该镜头尺度下增加面数/PBR 收益很低。
- **lesson**: 把主轴、transform、真实镜头尺寸、面数、纹理和包体作为路线探针；按目标画面选择档位。
- **scope limit**: 30k、1024、2–5MB 等数字不是跨资产硬门槛，必须由发布目标配置。

## HY-004 · GLB seam 拆点把闭合壳误报为 398 components

- **date**: 2026-07-13
- **scope**: 揭小贤 neutral A-pose；Hunyuan Pro 3.1 `Normal`、六个辅助视图、30k faces；Blender 5.1.2。
- **evidence**: route `jiexiaoxian-basemesh-challenger-v1`，revision `jxx-hunyuan-basemesh-r1`，probe `hunyuan-neutral-basemesh-001`，EvidenceBundle `evidence-753e5daf738e551fce85`；raw GLB SHA256 `1a7149d2eda6737a91968ae938610d6188d6a5fa6f941c2c5ace80271e9721bf`。
- **observation**: raw inventory 为 20,004 vertices、398 indexed components、9,350 boundary edges、5,002 duplicate-coordinate vertices。`1e-8` exact weld 后稳定变为 15,002 vertices、1 component、0 boundary、0 multi-face；说明主要是属性 seam 的索引拆点，不是肉眼可见的 398 块碎壳。
- **decision impact**: 原本基于 component/boundary 的直接 abandon 被撤回，候选进入一次无额外 API 成本的临时 rig probe；随后因随机 30k triangles、手脸无增益和目标姿势无优势而停止 direct-basemesh 路线。
- **lesson**: 对 provider GLB 先区分“索引/属性 seam”与“几何开裂”；exact-weld derivative + source hash lineage 是便宜判别器。component 数不能单独成为 kill gate。
- **scope limit**: 不推出所有 duplicate vertices 都可安全焊接，也不推出闭合就适合变形；UV、normal、材质 seam 和变形仍须分别复核。
- **retirement condition**: importer/provider 改变顶点属性编码，或新的 fixture 证明相同统计对应真实分离几何时重验。

## HY-005 · 智能拓扑的 OBJ 保留 quad，GLB 传输会三角化

- **date**: 2026-07-13
- **scope**: HY-004 同一 GLB 输入；Polygon 1.5 `topology.reduce`，`PolygonType=quadrilateral`、`FaceLevel=low`；Blender 5.1.2。
- **evidence**: revision `jxx-hunyuan-smart-topology-r2`，probe `hunyuan-smart-topology-lowquad-002`，EvidenceBundle `evidence-8861dcaf1c2d0812479f`；OBJ SHA256 `42ec4647893890fa8b1ee2231bf9c4ec4f9720404dc409a2123b1b9adeb2775c`。
- **observation**: companion GLB 导入为 9,865 triangle faces；同一结果的 OBJ 为 4,945 vertices、5,198 faces，其中 4,669 quads、529 triangles。OBJ body flow 明显比 raw 30k random triangles 规整，但 low 档损失脸、手和发型细节，并仍有 54 boundary edges、17 multi-face edges，主要落在下头/颈附近。临时自动权重能运行，但不构成生产批准。
- **decision impact**: GLB 继续用于自包含 shape Quicklook；polygon arity/edge-flow review 改以 OBJ 为权威。low 档只支持一次同输入 `quadrilateral + high` 对照，不进入 AutoRig/UV/衣服。
- **lesson**: 输出格式是证据合同的一部分。glTF primitive 的三角化不能证明 provider 忽略了 quad 请求；必须审查能保留多边形拓扑的 OBJ/FBX，并对账同一 JobHandle。
- **scope limit**: 不推出 OBJ 总是优于 GLB；GLB 仍适合自包含预览与 runtime。也不推出“90% quads”自动等于 deformation-ready edge flow。
- **retirement condition**: provider 开始返回可保留 quad metadata 的新格式，或官方输出合同改变时重验。

同一输入的 `FaceLevel=high` 后续对照还发现 provider OBJ 不保持统一单位尺度：low 高度为 `1.0`，high 约为 `1.898438`。对比板必须先记录原始 bounds，再在 derivative 中按高度归一化并使用相同相机；不能把 provider 的 scale drift 误写成角色比例变化。high OBJ 为 6,994 vertices、7,421 faces（6,562 quads / 859 tris），8 boundary / 1 multi-face 均落在头部区域。拓扑 reviewer 认为它足以提出一次 body-only A/B；公平归一化的 FBX visual review 则显示权威 source 在脸、肩臂、腹胯与线流上仍更好。Director 因没有净资产收益而停止 body-cage 投入，完整头手也明确不通过。

## HY-006 · Provider 逻辑类型与真实容器/附件不一致

- **date**: 2026-07-13
- **scope**: Hunyuan `geometry.pro` 与 `topology.reduce` live fetch；API version `2025-05-13`。
- **evidence**: HY-004/HY-005 route；adapter tests `test_obj_provider_type_can_download_a_verified_zip_bundle` 与 `test_topology_reduce_accepts_image_obj_and_glb_result_set`。
- **observation**: `geometry.pro` 逻辑 `Type=OBJ` 实际是 OBJ/MTL/texture ZIP；`topology.reduce` 官方/实跑结果集合包含 `IMAGE + OBJ + GLB`，其中 IMAGE 为 preview PNG。旧实现把 ZIP 写成 `.obj` 并过早标为 VERIFIED；旧 registry 又会拒绝 IMAGE 附件。
- **decision impact**: Adapter 分离 `provider_type`/`container_type`，安全解包并校验 OBJ dependency closure；topology preview 只作为 `preview_image`，以真实 PNG/JPEG 容器校验。历史错误 manifest 保留为 deviation，不原地追认。
- **lesson**: provider 枚举、URL 后缀与字节容器必须分别验证；辅助预览不能继承几何资产角色。
- **scope limit**: 当前只允许已记录的 OBJ ZIP 和 topology IMAGE 合同；未知容器继续 fail closed，不能泛化为自动解压任意 archive。
- **retirement condition**: 官方 ResultFile3Ds/File3D 合同或 recorded live envelope 变化时更新 fixture 与 allow-list。

## TRIPO-001 · 旧 v2 脚本不是当前 v3 Adapter

- **date**: 2026-07-13
- **scope**: 本地 `ar-3d-pipeline` 旧 skill 与 `scripts/tripo_gen.py`；Tripo 官方 v3 文档审计，未调用付费 API。
- **evidence**: `/Users/hhh0x/.claude/skills/ar-3d-pipeline/SKILL.md` 与仓库 `scripts/tripo_gen.py`；官方 v3 docs `https://developers.tripo3d.ai/en/docs`。
- **observation**: 本地没有独立 Tripo skill/adapter、recorded fixture 或 credentials。旧脚本使用 v2 聚合 endpoint、`urlretrieve`、进程内轮询、无幂等 reservation/原子落盘/hash/短期 URL 隔离，并会误处理非数字的新模型版本。官方当前主 API 为 `/v3`，提供 P1 direct low-poly、Smart Retopology、rig/retarget 等独立任务。
- **decision impact**: Tripo 将作为新的 provider adapter 构建，共享 submit/poll/fetch/manifest 状态边界；旧脚本只作为失败经验与字段迁移来源，不恢复为入口。
- **lesson**: provider 对照必须固定版本、输入和证据板，并比较可修 topology/目标姿势，不只比较预览。provider-specific action/path 留在 registry，共享 Harness 状态机。
- **scope limit**: 本 case 尚未证明 Tripo 输出优于 Hunyuan，也不固化旧 skill 中关于 quad/retarget 的过期结论。
- **retirement condition**: Tripo v3 adapter 获得 recorded/live fixtures 后，以新合同替换本审计条目中的推断。

## MAG-001 · 技术路线成立但作品仍像竖向视频窗

- **date**: 2026-06-26—2026-06-28
- **scope**: 功夫茶磁贴，AI/CG beauty + clean matte + SBS。
- **evidence**: `jieyanggucheng#59`、`#74`；v39/v40 与 v49A2 R02 v36/v32 记录。
- **observation**: shader、远程视频、SBS 编码均成立，但中段边缘由几何门洞或 slab 拥有，人物、桌椅、雨棚和店铺没有真实逐帧 owner，画面仍像一个视频矩形。
- **lesson**: 卡面路线需要让边缘跟随可见物体或经批准的 artist matte；runtime smoke 只回答播放问题。先做便宜的 edge-ownership/composite 探针，再做全长。
- **scope limit**: 不禁止矩形本身成为有意设计，也不要求所有 alpha 必须由 Blender 生成。

## MAG-002 · 单图直接接 runtime 与多版本创意漂移

- **date**: 2026-06-25—2026-06-27
- **scope**: 功夫茶 V4 及随后多条 2D/3D 路线。
- **evidence**: `jieyanggucheng#59`、`#74`。
- **observation**: 单张候选尚未证明物件舞台、破框和运动语法，就进入 runtime；之后出现大量低信息增益版本。
- **lesson**: 高代价实现前，先用与当前未知匹配的定帧、animatic 或小段 motion probe；是否赛马、候选数和评审角色由项目决定，不固定为统一 tournament。
- **scope limit**: 不要求所有简单修改都先做多候选定帧。

## MAG-003 · 审计 ID、guide matte 与最终 alpha 混用

- **date**: 2026-06-27—2026-07-07
- **scope**: 功夫茶与长龙的 object-pass、SAM2/roto guide、Object/Material Index 和 SBS 打包。
- **evidence**: `jieyanggucheng#59` 的 clean-pass 迭代、`#147` 的 P17–P40/P40R。
- **observation**: Object/Material Index 很适合找对象和排错，SAM2/背景移除也能提供 guide；但它们可能丢失抗锯齿、透明、motion blur 或真实 owner，直接进入 final alpha 时会暴露错误背景和硬边。
- **lesson**: 先声明输出需要的 alpha 语义，再选择同源 render、artist matte、roto 或混合方法；审计 ID 与 guide 默认不可发布。打包器只证明编码一致，不能批准上游 owner。
- **scope limit**: 不要求所有最终 alpha 都必须由 Blender object pass 生成；经目标镜头验证的 artist matte 可以成立。

## SPOT-001 · 全帧 AI 重渲无法拆成 live-AR 效果层

- **date**: 2026-07-04
- **scope**: 进贤门《叩城》；Seedance 全帧生成；实体与楼身重叠。
- **evidence**: `jieyanggucheng#140` 的 Route D/F 与“AR 可分解性 GATE”记录。
- **observation**: 天空纯光段可用差分或 luma 方法近似提取；楼身、卷轴重叠带会残留背景重绘，离线视频好看但无法稳定叠回实时相机。
- **lesson**: 景点路线先验证输出可分解性：additive light、带 alpha 实体或真实 runtime 3D；用重构/composite preview 比较，而不是只审完整离线视频。
- **scope limit**: 不否定 AI 作为元素工厂、纹理或参考；否定的是未经分解证明的全帧结果直接作为 live overlay。

## SPOT-002 · 虚拟运镜与真实相机冲突

- **date**: 2026-07-03 生产规则复盘
- **scope**: 扫真实建筑、效果层与手持手机相机叠加。
- **evidence**: `jieyanggucheng#135`、`#136`；旧 `jygc-spot-animation`。
- **observation**: 效果视频自身推拉摇移时，会与用户手机的真实运动叠加，贴楼关系穿帮。
- **lesson**: 默认用触发图/photo-match 作为效果相机合同；若要使用虚拟运镜，必须先提出能同时解释真实相机运动的新跟踪/渲染路线并做真机 probe。
- **scope limit**: 这不是对所有 AR 或实时 3D 相机的禁令，只针对固定效果层叠真实建筑的路线。

## SPOT-003 · Blender 手搭光效技术正确但观感“小气”

- **date**: 2026-07-04
- **scope**: 《叩城》S4 金榜升起，手摆 emission 几何与程序光效。
- **evidence**: `jieyanggucheng#140` 生产交接；用户否决“小气版”和“朴素无辉光版”。
- **observation**: 元素位置、分层和输出合同可成立，但光瀑、星芒、粒子与整体辉光语言没有达到目标帧的威严感。
- **lesson**: machine correctness 不判断美术完成度；先用目标帧和最小 lookdev probe 验证尺度、材质与光语言，再选择 Blender、AI 元素、合成或混合路线。
- **scope limit**: 不推出“Blender 做不了光效”或“必须使用 AI”。

## SPOT-004 · 临时触发图不具备生产条件

- **date**: 2026-07-03—2026-07-08
- **scope**: 进贤门旧实验 marker 与八景触发图盘点。
- **evidence**: `jieyanggucheng#135`、旧 `jygc-spot-animation`；历史 marker 为 1024×768，视角/遮挡/来源记录不足，后随脚手架删除。
- **observation**: 临时 marker 能证明识别链路，却缺少生产 photo-match 所需的原片、机位、焦距、EXIF 和清场条件。
- **lesson**: trigger-source probe 同时验证识别与渲染相机输入；压缩 marker 不能替代权威实拍源和 provenance。
- **scope limit**: 不把旧分辨率写成永久最低标准；目标镜头和 tracker 决定实际要求。

## CONTENT-001 · 景点史实与宗教表达红线

- **date**: 2026-07-03
- **scope**: 揭阳古城八景的文旅 AR 内容。
- **evidence**: `jieyanggucheng#135`；旧 `jygc-spot-animation` 八景表。
- **observation**: 曾出现无依据楹联、错误匾额或把神庙内容设计成显灵/祈福的风险；例如城隍庙没有“明镜高悬”匾。
- **lesson**: 史实和宗教表达属于项目内容 policy，发布前由内容 reviewer 核对来源；不要把它们伪装成 Blender 几何 gate。
- **scope limit**: 具体史料以项目权威内容卡为准，本 casebook 只保存为何需要核对。

## AUDIO-001 · “空手倒茶”式音画脱节

- **date**: 2026-06 复盘
- **scope**: 功夫茶及八景带声动画。
- **evidence**: `jieyanggucheng#59`、`#135`；旧 magnet/spot skills。
- **observation**: 声音描述了倒茶、叩击、钟声或纸展，但画面没有对应动作，静态帧评审也无法发现节奏脱节。
- **lesson**: 有 A/V 目标时，用带声视频或密集时间证据核对 cue 与动作；不要以单帧代替 motion/audio review。
- **scope limit**: 无声资产无需该探针。
