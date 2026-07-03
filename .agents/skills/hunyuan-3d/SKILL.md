---
name: hunyuan-3d
description: >-
  腾讯混元生3D(产品1804,ai3d.tencentcloudapi.com)的完整 API 能力 + "图生3D→绑骨→文生动作"实跑管线。
  当任务涉及:用腾讯混元做图生3D/文生3D、混元自动绑骨(AutoRigging)、**混元文生动作(text-to-motion,
  一句话生成角色动画=混元独门)**、把吉祥物/IP角色做成可动3D、混元积分/计费/签名/面数控制、
  或要在 Tripo/混元 两个3D后端间选型融合 —— 时使用。出现 混元生3D/HunyuanTo3D/ai3d/SubmitAutoRiggingJob/
  SubmitHunyuanTo3DMotionJob/HY-Motion/文生动作/混元绑骨/混元图生3D 等关键词也应触发,即使没说"skill"。
  ⚠️注:纯混元一站式出"可动角色"**不成立**(文生动作 RetargetFile 实证不出带 mesh 的角色)——必须配 Blender retarget,见 §5-B。
  本 skill 只聚焦混元 API 本身;完整 AR 角色管线的总地图与"Tripo vs 混元怎么选/融合"见 [[ar-3d-pipeline]];
  Tripo 后端见 [[ar-3d-pipeline]];最后一公里 retarget/清理/验证见 [[blender-mcp]]。
---

# hunyuan-3d — 腾讯混元生3D 全流程(图生3D · 绑骨 · 文生动作)

腾讯云**混元生3D**(产品 1804,接口域名 `ai3d.tencentcloudapi.com`)的完整 API 能力 + 一条**"保持角色形象 → 图生3D → 绑骨 → 文生动作"**的实跑管线。当任务涉及:图生3D/文生3D、给网格**自动绑骨(AutoRigging)**、**文生动作(text-to-motion,一句话生成角色动画)**、或要把一个吉祥物/角色做成"可动 3D"——用本 skill。

> 配套:**总地图/选型/Tripo-混元融合见 [[ar-3d-pipeline]]**(混元只是其中一个后端);Tripo 后端 [[ar-3d-pipeline]];Blender retarget/清理/验证 [[blender-mcp]];AR 落地 [[scenic-spot-ar]] / [[wechat-miniprogram-ar]];旧记忆 [[hunyuan-3d-pipeline]](本 skill 取代并纠正它)。

## ⚡ 先读:三条实跑血泪纠正(2026-06,基于官方132页PDF + 揭小贤实跑)

1. **🔴【实证定论】文生动作 RetargetFile 不出带 mesh 的角色动画——纯混元一站式闭环不成立,Blender retarget 必走**。`RetargetFile` 原文要"混元生3D动画生成的模型(动画模板的接口)",我曾推断=绑骨带 MotionType 的产物。**3 次实跑证伪**:(a)绑骨没 MotionType、(b)绑骨没 MotionType、(c)**绑骨带 MotionType=26** —— 文生动作输出**恒为 52 骨纯骨架 FBX(无角色 mesh,cm单位)**,三次 size 全 14770096,RetargetFile 对输出**毫无 mesh 效果**(被无视或只调比例仍不带 mesh)。**结论:要让角色动起来,必须本地 Blender 把这段 52 骨动作 retarget 到角色 rig(见 §5-B)。** [实测,非推断]
   - **但 MotionType 仍有用**:绑骨带 `MotionType=26`(待机)→ 绑骨产物 FBX **自带一个 Idle 动画**(待机 baked 在 28 骨 rig + mesh 上)→ 白送一个 Idle clip,省得另做。
   - **[文档背书,2026-06 通读全 1804 文档树]**:官方**没有任何端到端"图生3D→绑骨→动作→可动角色"教程**;快速入门只教图生3D 一个接口;**RetargetFile 全文档零示例**("动画模板的接口"这词只出现在那一行、不绑定任何 Action);EnableMesh 无条件说明。→ **"按文档纯混元能一站式"不成立,文档对这条链是空白的,实跑是唯一来源**(实跑=不能,得 Blender retarget)。
   - **二进制实证**:文生动作产物 FBX 里 Geometry/Vertices/Deformer=0(无蒙皮 mesh),但 material/texture 指向混元内部模板 `ComfyUI-HY-Motion-internal/.../boy_Rigging_smplx`(SMPL-X 假人)→ 证实 RetargetFile 没用上你的角色、挂的是内部 52 骨 SMPL-X 模板。
   - **想要"一站式"?那是另一个产品:混元3D Studio 网页版**(`3d.hunyuan.tencent.com/studio`,生成→自动绑骨→套动作库→导出带骨FBX,但动作库多为走/挥手类、礼仪类仍未必有)+ `混元3D MCP server` —— **都跟本 API(ai3d/产品1804)不同源,API 不能复刻 Studio 那条链**。
2. **图生3D 产物常比输入图整体歪~10°(轴不竖直)**。根因=单图重建缺多视图约束。修:① 源头用 **Model=3.1 + MultiViewImages 多视图(正/侧/背)** 重建压歪;② **绑骨前**在 Blender 把主轴扶正 + Apply Transform(歪的骨架会连骨一起歪,必须先正后绑)。
3. **面数要为手机控**(见 §手机面数)。`FaceCount` 默认 **500000(50万)对手机是灾难**,必须显式压到 2-4 万或用 LowPoly;且**混元官方零压缩**(KTX2/Draco/meshopt/LOD/纹理尺寸全无)→ 出 GLB 后**必须本地 gltf-transform 收尾**。

## 📱 手机面数方案(AR 角色必看)

| 项 | 目标 | 怎么做 |
|---|---|---|
| 面数 | **≤40k tris**(Q版 AR 理想 15–30k) | 生成时 `GenerateType=Normal + FaceCount=20000~40000`,或 `LowPoly`(3.0,FaceCount失效自动低面);已有高模用 `SubmitReduceFaceJob`(只 high/med/low 三档,50积分) |
| 纹理 | 1024(1K)够 Q版,最多 2048 | **`EnablePBR=false`**(PBR 多 3-4 张图、翻倍体积、移动端不需要);本地 resize 到 1024 |
| 体积 | **≤3–5MB** | 出 GLB 后本地 `gltf-transform`:meshopt 几何压缩 + WebP/KTX2 纹理 + resize。混元官方不给任何压缩,这步不能省 |

**[实测建表]**(本项目揭小贤,Pro 3.1 多视图,gltf-transform 量):
| 设置 | 实际 tris | 纹理 | GLB 原始 | 本地压后 |
|---|---|---|---|---|
| `FaceCount=30000` + 无PBR | **30k**(=FaceCount,"面"≈三角) | 1 张 | 20MB(纹理撑大) | **3.1MB**(纹理1024+meshopt) |
| `FaceCount=150000` + PBR | 150k | **3 张**(PBR=色/金属粗糙/法线) | 47.5MB | — |
→ **"面"≈三角面数,FaceCount 所见即所得**;**积分**:无PBR=40(Normal20+FaceCount10+MultiView10),PBR=50(+Pbr10)。
**[实证·选档结论]** 角色在 AR 里小(如门洞内 s≈0.11)→ **30k/无PBR/1024纹理(3.1MB)与 150k/PBR(47.5MB)在该尺寸下肉眼无差** → 小角色**别堆面/别开PBR**,纯浪费体积。Hero 大特写才考虑高面+PBR。
[仍未验] LowPoly 实际输出面数 / ReduceFace high-med-low 各档面数 / FaceCount 上限 150 万的产物 —— 需要时再实测。

## 0. 全局事实(所有 Action 通用,文档实锤)

- **域名** `ai3d.tencentcloudapi.com`(就近接入,仅非金融区);指定地域 `ai3d.ap-guangzhou.tencentcloudapi.com`。产物 COS 全在 **ap-guangzhou** → 用 `ap-guangzhou` 最稳。
- **Version 全部 Action 统一 = `2025-05-13`**(含绑骨/文生动作,无例外)。产品 1804 共 **19 个注册 Action**(= 约 9 个功能各 Submit+Query/Describe 成对 + 同步的 Convert3DFormat;下表按功能列 10 行)。
- **签名 TC3-HMAC-SHA256**,service=`ai3d`。实现见 `scripts/hunyuan3d_gen.py` 的 `call(action, payload)`,绑骨/动作直接复用,只换 `X-TC-Action` + body。
- **异步两段式**:`Submit*` 拿 `JobId`(有效期 24h)→ 轮询 `Query*`(图生3D)或 **`Describe*`**(绑骨/动作,注意命名不一致!)→ `Status ∈ {WAIT,RUN,FAIL,DONE}` → DONE 读 `ResultFile3Ds[].{Type,Url}`。**产物下载链有效期仅 1 天**。
- **凭证**:`~/.config/hunyuan/credentials`(`TENCENT_SECRET_ID=` / `TENCENT_SECRET_KEY=`,chmod 600,gitignore,**绝不硬编码/不进 repo**)。只有 SecretId 无法签名。
- **计费=积分制**:`QueryHunyuanTo3DProJob` 官方出参明确包含 `ResultCreditConsumed` + `ResultCreditDetails`(如 `{"FaceCount":10,"GenerateType-Normal":20,"Pbr":10}`);不要假设所有 `Query/Describe*` 都返回积分明细。各档各功能分别计费,动作/绑骨等接口以官方计费页、控制台账单和本项目实跑 manifest 为准。**`ResourceInsufficient`=积分/资源包不足 → 控制台买资源包**(与签名无关;签名错会直接报 auth/signature)。
- **并发**:Pro 3,其余(Rapid/绑骨/动作/纹理/拓扑/UV/组件)默认 **1**;频率 20 次/秒。
- **下载坑(实测)**:`urllib.urlretrieve` 拉 COS 产物常 `RemoteDisconnected` → **改用 `curl -sS -L --retry 3 -o`**。

## 1. Action 全清单(19 个注册名,按功能 10 行)

| Action(Submit / 查询) | 中文 | 用途 |
|---|---|---|
| `SubmitHunyuanTo3DProJob` / **`Query`**`HunyuanTo3DProJob` | 专业版图/文生3D | 主力,**支持多视图** §2 |
| `SubmitHunyuanTo3DRapidJob` / **`Query`**`HunyuanTo3DRapidJob` | 极速版图/文生3D | 更快更省,无多视图,可出 MP4 转盘 |
| `SubmitProfileTo3DJob` / **`Describe`**`ProfileTo3DJob` | 3D人物生成 | 真人头像→**预置IP模板**(非通用) |
| `SubmitAutoRiggingJob` / **`Describe`**`AutoRiggingJob` | 绑骨蒙皮 | §3,裸网格直喂 |
| `SubmitHunyuanTo3DMotionJob` / **`Describe`**`HunyuanTo3DMotionJob` | **文生动作** | §4,HY-Motion-1.0 |
| `SubmitTextureTo3DJob` / `Describe…` | 纹理生成 | 白模+参考图/文 重生贴图 |
| `SubmitReduceFaceJob` / `Describe…` | 智能减面/重拓扑 | 降面数 |
| `SubmitHunyuan3DPartJob` / `Query…` | 组件生成 | 按结构拆件 |
| `SubmitHunyuanTo3DUVJob` / `Describe…` | UV展开 | |
| `Convert3DFormat` | 格式转换 | OBJ/GLB/FBX/STL/USDZ 互转 |

> ⚠️ **查询端命名不一致**:图生3D Pro/Rapid/组件用 **`Query*`**;绑骨/动作/纹理/UV/Profile 用 **`Describe*`**。错了会 `UnsupportedOperation`。
> ⚠️ **没有**独立"查额度/查资产列表"接口;额度只能从 `ResultCreditConsumed` 反推 / 控制台看。
> ⚠️ **"标准版 Std"(`SubmitHunyuanTo3DJob`)已被官方删除**,别再找。当前只有 Pro + Rapid 两档。

## 1.1 API 能力矩阵(只看 API,不按 Studio UI 兜底)

本表用于判断"这一步能不能由混元 API 自动化"。**不要把网页 Studio 的人工工作台能力默认等同于 API 自动化能力**;本 skill 的执行边界只按 `ai3d.tencentcloudapi.com` 产品 1804 API。

| 生产环节 | API 自动化状态 | 主要 Action | 输入 | 必须落地的文件 | 不能省的 Blender / 人工步骤 | Gate 结论 |
|---|---|---|---|---|---|---|
| 概念设计 / 三视图设计 | **不由 1804 API 直接覆盖** | 无独立 concept-design Action | 文案、参考图、风格约束 | `concept_brief.md`,`front.png`,`side.png`,`back.png`,`material_ref.png` | 用图像模型/人工设计/Blender 渲出正侧背;人工确认 silhouette 和材质方向 | 没有三视图不得进几何生成 |
| 几何生成 | **可 API 自动化** | `SubmitHunyuanTo3DProJob` / `QueryHunyuanTo3DProJob`;Rapid 可选 | Prompt / 单图 / 多视图;`Model=3.1`;`FaceCount`;`GenerateType`;`EnablePBR` | `hunyuan_raw.glb|fbx|obj`,`query.json`,`download.log`,`preview_turntable.mp4` | Blender 导入检查主轴、比例、破面、材质、面数;必要时扶正并 Apply Transform | 只能作为 raw asset,不能直接进 final |
| 组件拆分 | **可 API 自动化,但本项目未深测** | `SubmitHunyuan3DPartJob` / `QueryHunyuan3DPartJob` | 3D 文件 URL,官方写明输入仅支持 FBX;可带 `PartSegmentationInfo`;可选 `EnableStagedGeneration` | `parts_raw/`,`part_manifest.json`,`part_segmentation_info.json` | Blender 检查组件命名、pivot、缝隙、重叠、pass owner;重新组织 collection | 未经 Blender 组件审查不得进入 pass |
| 低模 / 智能拓扑 / 减面 | **可 API 自动化,但需本地复核** | `SubmitReduceFaceJob` / `DescribeReduceFaceJob`;`GenerateType=LowPoly` | 高模 3D 文件 URL 或生成参数 | `reduced.glb`,`reduce_job.json`,`wireframe_board.jpg` | RetopoFlow/手工 retopo/Quad Remesher 二次清理;检查 deformation loop 和三角面分布 | Hero 变形资产不能只靠自动减面过关 |
| UV 展开 | **可 API 自动化,但需 DCC QA** | `SubmitHunyuanTo3DUVJob` / `DescribeHunyuanTo3DUVJob` | 3D 文件 URL | `uv_model.glb|fbx`,`uv_layout.png`,`uv_job.json` | Zen UV/UVPackmaster/Texel Density Checker 检查拉伸、重叠、边距、TD 一致性 | 没有 UV/TD board 不得进材质 |
| 纹理生成 / 纹理重绘 | **可 API 自动化,但不能替代美术验收** | `SubmitTextureTo3DJob` / `DescribeTextureTo3DJob` | 白模/UV 模型 + 参考图/文本;可多视图参考 | `textured_model.glb`,`textures/`,`texture_job.json`,`material_board.jpg` | Blender 材质节点、贴图路径、色彩空间、PBR/非PBR、近景材质统一;必要时 Poly Haven/手工贴图 | 近景材质必须过 closeup board |
| 绑骨蒙皮 | **可 API 自动化,主要适合人形/动物基础绑定** | `SubmitAutoRiggingJob` / `DescribeAutoRiggingJob` | GLB/FBX URL;可选 `MotionType` | `rigged.fbx`,`rig_job.json`,`rig_preview.mp4` | Blender 骨架检查、权重修正、极限姿态、多视图 rig harness;龙类长身体通常应自建 Spline IK/B-Bones rig | 只证明有骨架,不证明可动画 |
| 动画生成 | **可 API 自动化生成动作源,不是 final animated character** | `SubmitHunyuanTo3DMotionJob` / `DescribeHunyuanTo3DMotionJob` | 动作 prompt;duration;rewrite | `motion_source.fbx`,`motion_job.json`,`skeleton_strip.jpg` | Blender retarget 到目标 rig、scale/cm 修正、bake、动作多视图 harness;实测 `RetargetFile/EnableMesh` 不出带 mesh 成品 | 动作源可用,final 动画必须 Blender 验收 |
| 3D 人物生成 | **可 API 自动化,非通用道具/龙主线** | `SubmitProfileTo3DJob` / `DescribeProfileTo3DJob` | 人物头像图片 | `profile_model.glb|fbx`,`profile_job.json` | 仅在真人/IP 人形需要时使用;仍需 Blender QA | 不作为龙/建筑资产主线 |
| 格式转换 | **可 API 自动化** | `Convert3DFormat` | OBJ/GLB/FBX/STL/USDZ URL | `converted.*`,`convert_job.json` | Blender/assimp/gltf-transform 验证骨骼、动画、贴图、单位没有丢 | 转格式不等于验收 |

**一句话边界**:混元 API 可以帮我们生成 raw geometry、parts、topology、UV、texture、rig、motion source;**Blender harness 决定它能不能进入 AR 预渲染生产**。

## 1.2 Hunyuan → Blender 生产接力(每个模块都必须落地和验收)

每次调用混元 API 后,不得只保留临时 COS URL。所有产物必须落入候选目录并写 manifest。建议目录:

```text
.artifacts/hunyuan/<asset-id>/<run-id>/
  input/
    prompt.md
    front.png
    side.png
    back.png
    material_ref.png
  api/
    submit.json
    query-or-describe.json
    result_urls.txt
    download.log
  raw/
    hunyuan_raw.glb
    hunyuan_raw.fbx
  blender_check/
    import_report.json
    multiview_board.jpg
    wireframe_board.jpg
    material_board.jpg
    rig_or_motion_board.jpg
  manifest.json
```

### 概念 / 三视图 → 几何生成

- 输入:正面、侧面、背面、必要时 45°/材质参考。
- 落地:`concept_brief.md`、`front.png`、`side.png`、`back.png`。
- Blender 检查前置:无。先做人审,确认不是单张美图。
- 失败条件:三视图不一致、侧面无法支持体积、背面缺失、材质方向不清。
- 下一步:`SubmitHunyuanTo3DProJob` 多视图生成。

### 几何生成 → Blender import check

- 落地:raw GLB/FBX、job JSON、下载日志、预览图。
- Blender 检查:主轴是否歪、单位/scale、面数、破面、法线、纹理路径、主轮廓、近景读法。
- 失败条件:轴歪未修、洞/破面、形体不符合三视图、面数不可控、近景像低模玩具。
- 下一步:扶正 + Apply Transform;retopo/UV/material。

### 组件拆分 → Blender collection ownership

- 落地:拆分后的组件模型、组件 manifest、分割信息。
- Blender 检查:组件 pivot、命名、接缝、重叠、是否能映射到 pass owner。
- 失败条件:组件语义错、关键物体被拆碎、接缝明显、无法单独控制可见性。
- 下一步:重组 collection,写入 `PASS_*__ARTIST_FINAL_MASK_OBJECTS` 或 asset collection。

### 低模/拓扑 → Deformation QA

- 落地:reduced/lowpoly 模型、wireframe board、face-count report。
- Blender 检查:变形环线、三角面集中、关节区域 topology、近景硬边。
- 失败条件:龙身没有连续环线、弯曲处塌陷、自动拓扑破坏 silhouette。
- 下一步:RetopoFlow/手工 retopo/Quad Remesher 辅助。

### UV → Texel Density QA

- 落地:UV 后模型、UV layout、UV job JSON。
- Blender 检查:UV 重叠、拉伸、边距、UDIM/tiles、texel density。
- 失败条件:近景资产 TD 不一致、拉伸明显、贴图边缘会穿帮。
- 下一步:Zen UV/UVPackmaster/Texel Density Checker 修正。

### 纹理 → Material Lookdev

- 落地:textured 模型、贴图目录、材质 board。
- Blender 检查:色彩空间、PBR/非PBR、贴图路径、近景材质、与场景光照统一。
- 失败条件:贴图糊、AI 纹理漂移、缝合线明显、材质与台基/建筑/龙风格不一致。
- 下一步:Poly Haven/手工贴图/DECALmachine/材质节点精修。

### 绑骨 → Rig Harness

- 落地:rigged FBX、rig job JSON、动作模板信息。
- Blender 检查:骨骼命名、权重、极限姿态、broken constraints、单位、是否含 mesh。
- 失败条件:骨架歪、权重错、A/T pose 不干净、配饰拖拽、穿模、龙类资产无法沿身体连续弯曲。
- 下一步:人形可 retarget/bake;龙走 Blender Spline IK + B-Bones + Follow Path 自建 rig。

### 文生动作 → Retarget / Bake

- 落地:motion source FBX、motion job JSON、skeleton strip。
- Blender 检查:动作帧范围、cm scale、骨架层级、关键姿态、多帧可读性。
- 失败条件:动作不是 prompt 语义、抽搐、无可用 action、retarget 后翻倒。
- 下一步:retarget 到目标 rig,修 curve,bake action,输出多视图 animation harness。

## 1.3 Hunyuan 产物多视图 Harness(进入 Blender 前后都要看)

混元产物不能靠单张 preview 或一个 turntable 过关。每个进入后续阶段的 asset/action 都要输出固定视图。

### 模型 harness

必看视图:

- front
- back
- left
- right
- top
- 45-degree hero view
- camera-near closeup
- silhouette
- clay render
- wireframe
- UV / TD board
- material closeup

通过条件:主轴正、轮廓对、近景不低模、wireframe 可修、UV/材质可控。失败即回 Hunyuan 重跑或 Blender retopo/lookdev。

### 绑骨 harness

必看测试:

- neutral pose
- S curve
- C curve
- tight bend / coil
- over-under obstacle wrap
- near-lens rush pose
- extreme bend
- head/target aim
- appendage secondary motion

每个测试至少输出 camera/front/side/top/45°。通过条件:无断裂、无压扁、无 twist、无穿模、bake 后一致。失败即回 rig。

### 动画 harness

必看视图:

- main camera
- top path view
- side path view
- dragon-only / character-only view
- camera path board
- head/nose/tail motion path
- high-coverage frame contact sheet
- reference-vs-candidate timing board

通过条件:主视角好看,top/side 不穿帮,最高遮挡帧可读,动作不是路径平移。失败即回 blocking/polish。

> Blender 多视图 harness 的脚本、目录、boards、agent review 和 gate 细节应单独成 issue 维护;本 skill 只定义 Hunyuan 产物进入 harness 前后的硬要求。

## 1.4 官方文档核对补丁与项目硬状态(2026-07-02)

- `ResultCreditConsumed` / `ResultCreditDetails` 目前只在 `QueryHunyuanTo3DProJob` 官方出参中明确列出;不要假设所有 `Query/Describe*` 都返回积分明细。动作/绑骨等接口的积分以官方计费页、控制台账单和本项目实跑 manifest 为准。
- `SubmitHunyuan3DPartJob` 已支持 `PartSegmentationInfo` 和 `EnableStagedGeneration`;`QueryHunyuan3DPartJob` 可返回 `PartSegmentationInfo`。组件生成输入官方写明仅支持 FBX。开启 `EnableStagedGeneration` 会额外增加积分,必须写进 manifest。
- Pro 默认返回 OBJ+GLB;如显式使用 `ResultFormat`,必须记录是否产生额外积分。本项目移动端优先策略是:能用默认 OBJ+GLB 就不为 GLB 单独传 `ResultFormat`,除非实测 SDK/接口要求。
- 对组件、UV、纹理、Profile、Convert、LowPoly、ReduceFace 档位,矩阵行默认标注为"官方文档覆盖,项目未深测";只有跑过 artifact + Blender board 后才改为"项目实测"。
- `JXM_DRAGON_LIGHT_BODY_V01` 的 Hunyuan r1 当前只能标记为 `route_proof_only`:API job `DONE`,OBJ/GLB URL 和 preview URL 存在,但 raw GLB 尚未落本地且 manifest 记录过 `download_status=blocked_by_local_cos_tls_timeout`。在补齐 `raw/hunyuan_raw.glb`、`api/submit.json`、`api/query.json`、`api/result_urls.txt`、`api/download.log`、输入视图 hash、Blender model multiview board 和 wireframe board 前,不得进入 model fidelity / rig / animation gate。
- 对 AR 磁贴龙资产,Hunyuan 输出默认是 raw/source asset;未通过 Blender 扶正、retopo/UV/material、long-body rig harness、source pass board 和 fresh visual review 前,不得标为 final asset。

## 2. 图生3D — `SubmitHunyuanTo3DProJob`(主力)

文档 /1804/123447。入参三选一必填(`Prompt` / `ImageBase64` / `ImageUrl`),**文图互斥**(仅 `Sketch` 档可图+文)。

| 入参 | 约束 |
|---|---|
| `Model` | `3.0`(默认)/`3.1`;**3.1 时 LowPoly 不可用**,但多视图角度更多 |
| `Prompt` | ≤1024 字(Rapid 仅 ≤200) |
| `ImageBase64` | 单边 128–5000px,≤6MB;jpg/png/webp |
| `ImageUrl` | ≤8MB |
| `MultiViewImages.N` | **多视图重建**:每元素 `{ViewType, Url\|...}`。`ViewType` ∈ `left`/`right`/`back`(3.0);`top`/`bottom`/`left_front`/`right_front`(**仅3.1**)。主图走 `ImageBase64/ImageUrl`,其余视角放这里。总和 ≤8M |
| `EnablePBR` | 默认 false |
| `FaceCount` | 范围 [3000, 1500000](实测=三角面数,所见即所得);**默认值 500000 为 PDF 推断未亲验** → 反正**永远显式设**(手机 2-4 万),别赌默认;LowPoly 时失效 |
| `GenerateType` | `Normal`(默认,带纹理)/`LowPoly`(智能拓扑)/`Geometry`(白模)/`Sketch`(草图,可图+文) |
| `ResultFormat` | 默认出 `obj`+`glb`;可 STL/USDZ/FBX |

- **Rapid 档**(`SubmitHunyuanTo3DRapidJob`,/1804/123463,`Query…`):无多视图/无 FaceCount/无 GenerateType;`EnableGeometry` 出白模;`ResultFormat` 可出 **MP4** 转盘视频。
- 产物 GLB 偏重 → 配 `SubmitReduceFaceJob` 或本地 `gltf-transform` / `scripts/glb_cleanup_gold.py` 减面。移动端目标 ≤40k tris。

## 3. 绑骨 — `SubmitAutoRiggingJob`(/1804/131618,查询 `DescribeAutoRiggingJob`)

| 入参 | 约束 |
|---|---|
| `File3D` `{Url, Type}` | **必填,裸网格直喂**(不接 JobId)。`Type` ∈ `FBX`/`GLB`,≤60MB,`Url` 即模型直链(COS/公网)。**可直接喂图生3D 的 COS 产物 URL → 全链零外部托管** |
| `MotionType` | 1–48 **预设动作模板**(常用值见下行;完整 48 个见官方 /1804/131618)。**[实测]传一个(如 `26` 待机)→ 绑骨产物自带该段动画 = 白送一个 Idle clip**(做角色 Idle 最省事)。省略=只绑骨无动画。⚠️ 它**不能**让文生动作 RetargetFile 闭环跑通(那条实证不通,见⚡纠正1),传它只为拿 Idle。48 个全是战斗/位移/舞蹈,**无作揖**(拱手走 §4) |

- **硬要求(文档原文)**:人形须 **A-pose / T-pose**、尽量无动作;**不应含人体以外组件(武器/坐骑/翅膀)**、避免**松散衣物/配饰/复杂发型**。→ 角色带帽冠/手持道具/长袍要先在 Blender 去道具 + 摆 A-pose,否则绑歪/失败。
- 产物 = **FBX**(`auto_rigging/output/...`;Describe 出 `ResultFile3Ds` Array of File3D)。**[实测]** = ARMATURE **28 骨 + 角色 mesh** 都在;骨名是 **Mixamo 风格**(`root/Hips/Spine/Spine1/Spine2/Neck/Head/LeftShoulder/LeftArm/LeftForeArm/LeftHand/…/LeftUpLeg/LeftLeg/LeftFoot/ToeBase`),**但非保证 Mixamo 兼容(只 28 骨、无手指骨)**。权重蒙皮 OK(mesh 跟骨动)。配饰容忍:实测带帽冠+手持道具+长袍也能绑出可用 rig(虽违反"无配饰"建议,越干净越稳)。
- **48 个 MotionType(全是战斗/位移/舞蹈,无拱手作揖)**——常用挑这几个就够:**26/27=待机(做 Idle 最常用)**、23/24/25=走路、32/33=慢跑、34=奔跑、20=打太极、21=后空翻、28=街舞、38/46=原地跳。其余多为格斗(1回旋踢…48发送冲击波)。**礼仪/拱手 48 档里没有 → 拱手必走文生动作 §4 + Blender retarget。**

## 4. 文生动作 — `SubmitHunyuanTo3DMotionJob`(/1804/131256,查询 `DescribeHunyuanTo3DMotionJob`)★

**这是真·文生动作(HY-Motion-1.0),不是选模板**。一句话文本 → 角色动画,输出带动画 **FBX**。

| 入参 | 约束 |
|---|---|
| `Prompt` | **必填,≤128 字**自由文本动作描述(中/英),如 `双手抱拳拱手作揖鞠躬行礼` |
| `Model` | 默认 `HY-Motion-1.0` |
| `RetargetFile` `{Url,Type}`(InputFile3D) | 文档原文:「需重定向的模型地址,只能支持混元生3D动画生成的模型(动画模板的接口)」。**🔴[实测无效]** 传绑骨产物(含**带 MotionType** 的)输出**仍是纯骨架、无角色 mesh** → 别指望,见⚡纠正1 |
| `Duration` | 默认 5s,范围 **1–12s** |
| `EnableMesh` | 文档:默认 **true**,"返回的 fbx 是否带蒙皮 mesh"。**🔴[实测无效]** =true 时产物仍纯骨架,且 `ResultFile3Ds` **只 1 个文件**(没有另外的 mesh 文件) |
| `EnableRewrite` | prompt 自动扩写,默认 false(建议开,补全动作语义) |
| `EnableDurationEst` | 按 prompt 自动配时长 |

**实跑实证(本项目,揭小贤拱手)**:
- ✅ Prompt `双手抱拳于胸前,拱手作揖,身体微微前倾鞠躬行礼,传统中式拜礼` + `Duration:4 EnableRewrite:true` → ~20s DONE,出 14.7MB FBX。多帧帧条核验:双手从两侧抬起**合于胸前** + 头/躯干**前倾鞠躬** + 回正,**确是拱手作揖**(远好于手 K)。**HY-Motion 能听懂中式礼仪类自然语言**。
- ⚠️ **产物 FBX 实测=骨架-only**(52 骨人形 + 几个 EMPTY,**无 skinned mesh**,即便 `EnableMesh` 默认 true);单位 **cm(scale 0.01)**;`bpy.data.actions` 可能空(动画在 armature animation_data),取帧范围要从 `armature.animation_data.action.frame_range` 拿。**无 mesh 时验证动作**:渲染各 pose bone 的 head 世界坐标成"关节球帧条"(`scripts/render_skeleton_anim.py`)。
- 🔴 **[实证定论]RetargetFile + EnableMesh 都不出带 mesh 的角色**:3 次实跑(不传 / 传绑骨无MotionType产物 / 传绑骨带MotionType=26产物)输出**恒为 52 骨纯骨架**,`ResultFile3Ds` 恒 **1 个文件**(Type=FBX)。**纯混元产不出"可动角色",拱手→揭小贤必须本地 Blender retarget(见 §5-B 命令序列)。**
- **出参结构**[文档]:Submit→`JobId`+`RequestId`(无 mesh 出参);Describe→`Status`/`ErrorCode`/`ErrorMessage`/`ResultFile3Ds`(Array of File3D)/`RequestId`。`File3D`={`Type`,`Url`(有效期24h),`PreviewImageUrl`}。

## 5. 推荐管线:保持角色形象 → 可动 3D(标 ✅实锤/🔶推断/❓待验)

**A. 全混元闭环 —— 🔴实证不通,别走**(留作记录:RetargetFile 不出带 mesh 的角色,见⚡纠正1。下列步4 拿不到带 mesh 成品):
1. **图生3D** `SubmitHunyuanTo3DProJob`(`Model:3.1`+`MultiViewImages`正/侧/背=保形象+压轴歪;`GenerateType:Normal`+`FaceCount:20000~40000`+`EnablePBR:false`=手机面数)→ 出 GLB(COS url U1)。✅
2. **Blender 中转(关键,别跳)**:把 U1 **扶正主轴+Apply Transform**(修 tilt)+ **去道具(醒狮)+ 摆 A-pose**(绑骨硬要求)→ 重新上传得公网/COS url U1'。✅
3. **绑骨** `SubmitAutoRiggingJob`(`File3D.Url=U1'` + **`MotionType=26`(待机,必须传!)**)→ 绑骨+模板动画 FBX(U2)。✅链 **⚠️没传 MotionType=闭环必断(见⚡纠正1)**
4. **文生动作** `SubmitHunyuanTo3DMotionJob`(`RetargetFile.Url=U2` + 拱手 Prompt + `EnableMesh:true`)→ 带角色 mesh 的拱手动画 FBX。🔶(官方设计闭环,需实跑坐实 RetargetFile 真收 U2 且真带 mesh)
5. FBX→GLB+本地 meshopt+KTX2 落 AR。✅

**B. 混元 mesh+动作 + 本地 Blender retarget —— ✅唯一实证可跑通的路(本项目揭小贤即此)**:
1. **图生3D** Pro `Model=3.1`+多视图+`FaceCount=2~4万`+`EnablePBR:false` → 上正(多视图压歪)、30k tris 的角色 GLB。✅
2. **绑骨** `SubmitAutoRiggingJob`(`File3D.Url`=图生3D的COS url直喂 + **`MotionType=26`**)→ 28骨 rig + mesh + **自带待机Idle** FBX。✅(MotionType 白送 Idle,见⚡纠正1)
3. **文生动作纯文本**(不传 RetargetFile,反正没用)→ 混元通用人形拱手 FBX(52骨骨架-only)。✅
4. Blender `scripts/retarget_bake.py`:把拱手 retarget 到步2的28骨 rig,**保留待机→Idle clip + bake拱手→Gongshou clip(两动作 ACTIONS mode 一并导出)**;顺手纹理压1024。**铁坑**:源参考用动作 **frame-1 当共享 neutral**(非骨 edit-rest,否则 A/T-pose 错位致整体翻倒);**逐骨 DAMP**(冠/头 freeze 保威严、脊 0.45、臂 1.0,否则混元原拱手头部108°会甩翻大冠)。✅
5. `gltf-transform` meshopt 收尾 → ≤5MB 落 AR。✅本项目最终 3.1MB / Idle+Gongshou。

> 选型:**A 实证不通(RetargetFile 不出 mesh),不要再试**;**B 是唯一跑通的**。要纯一站式不碰 Blender → 目前混元做不到,等官方修 RetargetFile。

### 5-B 照敲命令序列(本项目实跑·可复制)

```bash
# 0) 准备角色 4 视图(正/左/右/背,透明底):Blender 渲 or 直接出图。FaceCount 想小直接生成时控。
# 1) 图生3D Pro 3.1 多视图(多视图压轴歪+保形象;CLI 暂无多视图,用内联 call() 见本项目 /tmp/hy_multiview.py 模板):
#    payload = {Model:"3.1", ImageBase64:<front>, MultiViewImages:[{ViewType:"left",ViewImageBase64:..},
#               {ViewType:"right",..},{ViewType:"back",..}], GenerateType:"Normal", FaceCount:30000, EnablePBR:False}
#    SubmitHunyuanTo3DProJob → QueryHunyuanTo3DProJob 轮询 DONE → 得 GLB 的 COS url U1
# 2) 绑骨 + 白送 Idle(MotionType=26 待机):File3D.Url 直接喂 U1(COS url,无需自己托管)
python3 scripts/hunyuan_anim.py rig --file-url "<U1>" --file-type GLB --motion-type 26 --out rigged.fbx
#    → rigged.fbx = 角色 mesh + 28 骨 + 待机Idle;也记下它的 COS url U2(RetargetFile 实测没用,可忽略)
# 3) 文生动作纯文本出拱手骨架(不传 retarget):
python3 scripts/hunyuan_anim.py motion --prompt "双手抱拳于胸前,拱手作揖,身体微微前倾鞠躬行礼" \
        --duration 4 --rewrite --out gongshou.fbx     # 产物=52骨骨架-only,cm单位
# 4) Blender retarget:把拱手 bake 到 rigged.fbx 的 28 骨,保留待机→Idle、拱手→Gongshou,纹理压1024,导出 GLB
blender -b -P scripts/retarget_bake.py -- rigged.fbx gongshou.fbx out_anim.glb
#    retarget_bake.py 内部已固化两条铁坑(改它顶部常量调):
#      MAP    = 目标28骨 ← 源52骨 的骨名映射(Hips←Pelvis / Spine←Spine1 / LeftArm←L_Shoulder …)
#      DAMP   = 逐骨幅度:Head/Hips=0(冻住保大冠不翻) Spine*=0.45 臂*=1.0 腿*=0.25
#      源参考 = 动作 frame-1 当共享 neutral(非骨 edit-rest;否则 A/T-pose 错位整体翻倒)
# 5) 收尾 + 验证:
npx -p @gltf-transform/cli gltf-transform optimize out_anim.glb final.glb --compress meshopt   # 或 Blender 已压纹理
blender -b -P scripts/render_glb_anim.py -- final.glb /tmp/frames 8 480 0   # 多帧帧条核动作(动画必看多帧非单帧)
```

## 6. 脚本(本项目 `scripts/`)

- `hunyuan3d_gen.py` — 图生3D Pro/Rapid:`submit|query|gen --image|--image-url|--prompt --format GLB --pbr --faces --type`。含签名 `call()`。
- `hunyuan_anim.py` — 绑骨+文生动作:`motion --prompt --duration --rewrite [--retarget-url --retarget-type] --out x.fbx`;`rig --file-url --file-type GLB [--motion-type N] --out x.fbx`;原子 `submit-*/describe-*`。复用 `hunyuan3d_gen.call`。
- `render_threeview.py` — GLB 渲正/侧/背三视图(喂多视图图生3D)。
- `render_skeleton_anim.py` — 骨架动画→关节球帧条(无 mesh 时验动作)。
- `render_fbx_anim.py` — 带 mesh 的 FBX 动画多帧帧条。

## 7. 验证状态

**✅ 已实证定论(本项目实跑):**
- `RetargetFile` / `EnableMesh` **都不出带 mesh 的角色**(3 次实跑,恒 52 骨纯骨架,ResultFile3Ds=1 文件)→ 纯混元闭环不通,Blender retarget 必走。
- 绑骨输出 FBX 骨架 = **28 骨 Mixamo 风格骨名**(非保证 Mixamo 兼容、无手指),带蒙皮 mesh,可被 Blender retarget(B 路已跑通)。
- 文生动作产物 = 52 骨纯骨架、cm 单位、**~30fps**(120 帧/4s),一次一段动作(多动作多次调)。
- FaceCount=所见即所得(三角面);图生3D 积分:无PBR 40 / PBR 50;多视图压轴歪有效。

**❓ 仍未验(需要时再跑):**
- LowPoly 实际输出面数 / ReduceFace high-med-low 各档面数 / FaceCount 默认值。
- 绑骨、文生动作的积分单价(我那两次 `ResultCreditConsumed` 返回 None,未拿到)。
- 各 Action 在 ap-guangzhou 以外地域的实际可用性。
- 文生动作 prompt 能描述的动作边界(礼仪类已验可行;复杂多段未试)。

## 8. 纠错备忘(对旧记忆 hunyuan-3d-pipeline)

①FaceCount 默认 **500000(PDF推断未亲验,永远显式设)**;②Pro FaceCount 范围 [3000,1.5M](40000 起是 intl SDK 旧注释);③**Std 已删**;④绑骨/动作查询端是 **`Describe*`** 不是 `Query*`;⑤COS 下载用 **curl 不用 urlretrieve**;⑥文生动作产物**骨架-only、cm 单位**。
