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
