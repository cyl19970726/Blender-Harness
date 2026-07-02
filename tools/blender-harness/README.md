# Blender Harness

Agent 在 Blender 里的作业环境(issue #131),不是"渲染完跑一下"的 QA 工具。#130
定义生产宪法(Phase + Gate),#131 定义这套环境本体,本 issue(#133)回答它在仓库
里住哪、长什么结构。

## 定位:感知 / 行动 / 反馈三层

| 层 | 是什么 | 交付物 | 本 PR 状态 |
|---|---|---|---|
| 感知层(agent 的眼) | 固定多视图 / board / filmstrip / 参考并排 | 内环 quicklook + 外环正式 board | 未落地(PR-3) |
| 行动层(agent 的手) | 参数化脚本动词;插件 = 动词扩展 | `blender/render_*` / `blender/audit_*` | 未落地(PR-3) |
| 反馈层(环境的判定) | gate 状态机 + 聚合判定 + 金反例回归 | 双 schema + `check-gate-status.mjs` + regression | **本 PR 交付** |

反馈层刻意最先构建:没有一个能真正拒绝产物的判定器,感知层拍出再多板子也只是
装饰。核心设计约束——**观察 ≠ 奖励**:agent 用自己的眼睛(感知层)干活,但通过
权只在独立评审手里,不在生产者自己手里。

## 目录结构

```text
tools/blender-harness/
├── README.md                 ← 本文件
├── package.json              ← npm test = 反馈层回归(零依赖)
├── schemas/
│   ├── gate-status.schema.json   ← <candidate-dir>/gate-status.json 的契约
│   └── review.schema.json        ← <candidate-dir>/reviews/<role>-review.json 的契约
├── src/
│   ├── check-gate-status.mjs     ← 聚合判定 CLI(反馈层核心)
│   └── run-regression.mjs        ← npm test 入口,子进程调用 checker 做回归断言
├── fixtures/
│   ├── gate-d-v01-negative/      ← 金反例(真实 Gate D 候选,已被独立评审拒绝)
│   └── synthetic-accepted-control/ ← 正控(纯合成,证明 checker 的 accepted/exit 0 路径)
└── blender/                  ← 行动层动词占位,PR-3 落地(见下方动词表)
```

## 动词表

按运行时分层是结构性约束(issue #131):反馈层纯 node、无 Blender 依赖,可以进
CI 每个 PR 自动跑;行动层要跑 `blender -b`,不进 CI,只在本机/渲染节点执行。

| 动词 | 路径 | runtime | 状态 |
|---|---|---|---|
| 聚合判定 | `src/check-gate-status.mjs` | `node` | 已落地(本 PR) |
| 回归自检 | `src/run-regression.mjs` | `node` | 已落地(本 PR) |
| 固定视图库 | `blender/lib/cameras.py` | `python3`(供 `blender -b` 调用) | 占位,PR-3 |
| IO/manifest 公共件 | `blender/lib/harness_io.py` | `python3` | 占位,PR-3 |
| board/filmstrip 排版公共件 | `blender/lib/boards.py` | `python3` | 占位,PR-3 |
| 内环速览 | `blender/quicklook.py` | `blender -b --python` | 占位,PR-3 |
| 模型多视图 | `blender/render_model_multiview.py` | `blender -b --python` | 占位,PR-3 |
| 绑骨姿势板 | `blender/render_rig_pose_board.py` | `blender -b --python` | 占位,PR-3 |
| 动画多视图 | `blender/render_animation_multiview.py` | `blender -b --python` | 占位,PR-3 |
| Pass 视图层构建 | `blender/build_source_pass_view_layers.py` | `blender -b --python` | 占位,PR-3 |
| Pass 渲染 | `blender/render_source_passes.py` | `blender -b --python` | 占位,PR-3 |
| Pass 产出审计 | `blender/audit_pass_outputs.py` | `blender -b --python` 或 `python3` | 占位,PR-3 |
| SBS/alpha 打包 | `blender/package_sbs_alpha.py` | `python3` | 占位,PR-3 |

## 用法

### CLI:check-gate-status

```bash
node src/check-gate-status.mjs <candidate-dir>
node src/check-gate-status.mjs <candidate-dir> --json
```

`<candidate-dir>` 是参数,禁止硬编码具体候选路径(issue #131 横切验收标准 1:
一切 render/board/audit/check 脚本必须以 candidate-dir 为参数)。目录内必须有
`gate-status.json`,以及 `reviews[].file` 指向的每个 review 文件(相对候选目录
或绝对路径)。

退出码:

- `0` = accepted —— 声明为 accepted-family 状态,且每个 `required_reviews`
  角色都有一条 `verdict: accept` 的 review。
- `1` = rejected / blocked —— 任一 required review 缺失、任一 required review
  `verdict` 为 `reject` 或 `conditional`、状态本身不是 accepted-family、或存在
  `forbidden_next_outputs` 命中。
- `2` = 契约违规或输入缺失 —— `gate-status.json`/`review.json` 缺失或不符合
  schema 形状,或 `status` 与 `downstream_allowed` 内部不一致(见下方聚合规则)。

### npm test

```bash
cd tools/blender-harness
npm test
```

零依赖,`node src/run-regression.mjs` 把 checker 当真实子进程调用,针对
`fixtures/` 跑 4 条回归断言(见下方"fixtures 说明")。CI 用同一条命令(见下方
"CI")。

## 聚合规则(issue #131 hardening,checker 硬编码,不做成可配置项)

1. 任一 `required_reviews` 角色在 `reviews[]` 中缺失 ⇒ 聚合结果 rejected
   (exit 1)。
2. 任一 required review 的 `verdict` 为 `reject` ⇒ rejected(exit 1);
   `verdict: conditional` **不解锁下游**,同样 rejected(exit 1),但诊断消息与
   `reject` 区分,便于定位是"硬拒"还是"有条件但未过关"。
3. `status` 不属于 accepted 族(`accepted` / `production_accepted`)时,
   `downstream_allowed` 必须为 `false`;`status` 属于 accepted 族时,
   `downstream_allowed` 必须为 `true`。两个方向的不一致都是**契约违规**
   (exit 2),而不是普通 reject——状态机本身撒谎,比某次评审没过关更严重。
4. `runtime_smoke_passed` **永不**等价于或自动升级为 `production_accepted`。
   `runtime_smoke_passed` 只证明微信小程序 runtime 路径能加载候选产物,不是
   生产验收。若 `status: runtime_smoke_passed` 却 `downstream_allowed: true`,
   同样按规则 3 判为契约违规。
5. `forbidden_next_outputs` 中任一路径/glob 在候选目录内实际存在,且候选未处
   于 accepted 状态 ⇒ rejected(exit 1)。这是下游绕过检测:防止"评审没过,但
   下游产物已经手工塞进候选目录"这种物理绕过。
6. 退出码总表:`0` = accepted,`1` = rejected/blocked,`2` = 契约违规或输入
   缺失。**metrics 只有拒绝权**:checker 输出 `accepted`(exit 0)仅代表
   "评审记录齐全、结构合法、且全部 accept",**不代表视觉背书**。视觉背书只存
   在于被引用的 `reviews/*.json` 内部——checker 能阻断晋级,但不能替独立评审
   签发"好看"。

## fixtures 说明

- `fixtures/gate-d-v01-negative/`:**金反例**。真实 Gate D 121 帧候选
  (`gate-d-reduced-animation-candidate-v01`),独立视觉评审已判 REJECT(高覆盖
  帧读成低模代理球/管,而非叙事驱动的龙形遮挡)。裁剪自
  `legacy/`(manifest/audit/review + 关键 boards,~1MB),461MB 全量素材归档位置
  与 SHA-256 记在该目录 `README.md`。此 fixture 必须**永远**判 rejected;若
  未来某个 checker 实现让它变成 accepted 或 `downstream_allowed: true`,那是
  checker 的 bug,不是 fixture 的 bug。
- `fixtures/synthetic-accepted-control/`:**正控**,纯合成 JSON,不带任何媒体
  文件、不代表任何真实视觉评审结果。唯一作用是证明 checker 的
  accepted/exit 0 路径本身可达——不能拿它当"某个 Gate 真的过了"的证据。

`npm test` 在这两个 fixture 之外,还在 `os.tmpdir()` 的临时目录里对 fixture
做篡改拷贝(从不修改被 git 跟踪的 fixture 本身),验证:(c) 删掉一个 required
review ⇒ exit 1;(d) 让 `downstream_allowed` 在 rejected 状态下翻转为 `true`
⇒ exit 2。四条断言合起来覆盖聚合规则 1/2/3/6。

## 后续 PR 路线(issue #133)

本 PR(PR-1)只交付地基:包骨架 + schemas + checker + 金反例/正控 fixtures +
CI 接线,对应反馈层。

- **PR-2 章程与契约**:`docs/pipeline/` 生产章程(泛化版
  GOAL_PRINCIPLES_ACCEPTANCE)、`docs/research/ar-magnet/reference-grammar/`
  参考锚导入、`rubrics/rubric-v01.md` + `rubrics/failure-modes.md`、
  hunyuan-3d skill 落 main。
- **PR-3 起动词**:`blender/lib/`(`cameras.py` / `harness_io.py` /
  `boards.py`)+ `blender/quicklook.py` + `blender/render_model_multiview.py`,
  其余动词按 #131 动工顺序逐个 PR 补齐,对应感知层与行动层。

详见 #133(包结构与落地路径)与 #131(harness 本体设计)。
