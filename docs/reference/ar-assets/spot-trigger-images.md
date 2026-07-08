---
status: deliverable
carrier: repo-docs
owner: longling
last-reviewed: 2026-07-09
related:
  - docs/prd/checkin-passport.md
  - docs/reference/ar-assets/manifest.json
  - docs/reference/ar-assets/fridge-magnets.md
  - docs/architecture/ASSET_LAYOUT.md
  - docs/decisions/0006-mini-program-ar-mainline.md
---

# 景点 AR 触发图台账

本台账登记「12 个景点点位」各自的 **AR 触发图**(实拍锚点，供 VisionKit 图像追踪识别用)现存与缺口情况，让文档里能直接看到每个景点有没有触发图、缺哪些。

- **权威景点清单来源**:`shared/domain/stamps.ts` 的 `STAMP_DEFINITIONS`(12 条，`spotCode` / `spotName` 以代码为准）。
- **产品拍板**:每景点配「日间版 + 夜间版」两张触发图,详见 [`../../prd/checkin-passport.md`](../../prd/checkin-passport.md) §4.1 **D1**(2026-07-08 产品拍板)。
- **资产落点铁律**(见 [`../../architecture/ASSET_LAYOUT.md`](../../architecture/ASSET_LAYOUT.md)):
  - 触发图**源片**(实拍原片 + 机位/时段记录）→ `_assets-src/triggers/<spot>/` + 同目录 `PROVENANCE.md`。
  - **生产 marker**(压缩版,小程序 AR 页唯一引用）→ `wechat-gucheng/miniprogram/ar/assets/markers/<spot>-marker.jpg`。
  - 三类图**严禁混放**:参考图 / 触发图 / 动画美术图物理目录分离。
- 状态口径参照 [`manifest.json`](manifest.json)。**缺就如实标缺** —— 这正是本台账要暴露的。

> ⚠️ **盘点结论(2026-07-09)**:全仓当前**没有任何一个景点的触发图**(实拍锚点/marker)。历史上的实验脚手架(`wechat-ar/`、`wechat-jinxianmen/`)及其散放的触发图/marker、以及 H5 磁贴卡面,均已在 2026-07-08 脚手架清理与 2026-07-03 H5 退役中物理删除。`_assets-src/triggers/` 和 `wechat-gucheng/miniprogram/ar/assets/markers/` 目录**尚未建立**。因此下表 12 行全部为「❌ 缺」;这是当前真实状态,不是登记遗漏。恢复入口 = tag `h5-final` / git 历史 `@03940cf8`,但按 ASSET_LAYOUT 铁律**不倒查补齐旧触发图**,新景点触发图产出即按新路径落地。

## 主表:12 景点触发图覆盖

| 景点代码 | 名称 | 日间版触发图 | 夜间版触发图 | 状态 |
| --- | --- | --- | --- | --- |
| JXM | 进贤门 | ❌ 缺 | ❌ 缺 | 未产出 |
| XG | 行彩桥 | ❌ 缺 | ❌ 缺 | 未产出 |
| SFS | 揭阳学宫 | ❌ 缺 | ❌ 缺 | 未产出 |
| CHM | 城隍庙 | ❌ 缺 | ❌ 缺 | 未产出 |
| YSF | 双峰寺 | ❌ 缺 | ❌ 缺 | 未产出 |
| FZC | 青狮守太平 | ❌ 缺 | ❌ 缺 | 未产出 |
| HOTEL01 | 榕江夜游 | ❌ 缺 | ❌ 缺 | 未产出 |
| SNACK01 | 英歌战舞 | ❌ 缺 | ❌ 缺 | 未产出 |
| WCS | 古城夜游记 | ❌ 缺 | ❌ 缺 | 未产出 |
| RJJ | 古城食单会 | ❌ 缺 | ❌ 缺 | 未产出 |
| QYJ | 嵌瓷工艺点 | ❌ 缺 | ❌ 缺 | 未产出 |
| GCX | 文创手工坊 | ❌ 缺 | ❌ 缺 | 未产出 |

### 汇总

- **日间版**:**0 / 12** 有图。
- **夜间版**:**0 / 12** 有图。
- **完全空缺**(日夜双缺)清单:`JXM` `XG` `SFS` `CHM` `YSF` `FZC` `HOTEL01` `SNACK01` `WCS` `RJJ` `QYJ` `GCX` —— **12 个景点全部空缺**。

> 说明:上表列的是「景点触发图」(扫**真实景点/建筑/装置**的实拍照,AR 识别锚点),不是「磁贴卡面触发图」(扫**印刷卡**),两类分开盘点。夜游类景点(HOTEL01/WCS 及夜间场次)的「日/夜双版」尤其关键,是 D1 拍板的直接动因。

## 磁贴卡面触发图盘点

「磁贴卡面触发图」= 扫描印刷磁贴/文创卡的卡面(印刷平面,非实景)。逐 SKU 处置见 [`fridge-magnets.md`](fridge-magnets.md)。

| SKU slug | 卡面触发图 | 状态 |
| --- | --- | --- |
| gongfucha(功夫茶) | ❌ 缺 | H5 磁贴卡面随 H5 退役物理删除 |
| haolao(蚝烙) | ❌ 缺 | 同上 |
| hongtouchuan(红头船) | ❌ 缺 | 同上 |
| jinxianmen(进贤门磁贴) | ❌ 缺 | 同上;勿与景点线郭之奇 AR 混淆 |
| nanpu-yuge(南浦渔歌) | ❌ 缺 | 视频贴卡路线已否决(rejected),仅证据留痕 |
| puning-dougan(普宁豆干) | ❌ 缺 | 同上 |
| shuangfeng-qifu(双峰祈福) | ❌ 缺 | 同上 |

- **磁贴卡面触发图**:**0 / 7** SKU 现存卡面图。原 `public/ar/magnets/*` 目录及其中所有 `.mind`/磁贴/卡面文件已于 2026-07-03 H5 退役中随路由物理删除;`fridge-magnets.md` 表格记录的是历史处置判断,对应像素文件已不在仓。恢复入口同为 tag `h5-final` / `@03940cf8`。

### 唯一相关的现存 IP 素材(非触发图,勿混用)

仓内唯一与 AR 相关的现存人物像素资产是 **揭小贤拍照姿势素材**(`wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/`)。它们是 checkin PRD §4.1 **D5「拍照合照点(彩蛋)」** 复用的姿势素材(定格帧 + 截屏合成),**不是景点触发图、也不是磁贴卡面**,列此仅为避免下游误当触发图使用。

| 用途 | 文件 | 尺寸 | 大小 | 预览 |
| --- | --- | --- | --- | --- |
| 比心 | `jiexiaoxian-photo-heart.png` | 611×611 | 972K | ![heart](../../../wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/jiexiaoxian-photo-heart.png) |
| 作揖 | `jiexiaoxian-photo-bow.png` | 611×611 | 940K | ![bow](../../../wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/jiexiaoxian-photo-bow.png) |
| 灯笼 | `jiexiaoxian-photo-lantern.png` | 611×611 | 940K | ![lantern](../../../wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/jiexiaoxian-photo-lantern.png) |
| 击掌 | `jiexiaoxian-photo-highfive.png` | 611×611 | 924K | ![highfive](../../../wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/jiexiaoxian-photo-highfive.png) |
| 合照框 | `jiexiaoxian-photo-poses-contact.png` | 1254×1254 | 2.1M | ![poses-contact](../../../wechat-gucheng/miniprogram/assets/jiexiaoxian-ui/ar-photo/jiexiaoxian-photo-poses-contact.png) |

## 补图规范

补齐 12 景点触发图时按以下要求执行:

1. **日/夜双版(D1 拍板)**:每景点产出「日间版 + 夜间版」两张触发图,同一场景挂两个 `xr-ar-tracker` 指向同一份 AR 内容,提升全天可触发率。**单场景活跃触发图以 2–3 张为上限**,不可无限堆叠(marker 越多识别负担/误触发越高)。见 [`../../prd/checkin-passport.md`](../../prd/checkin-passport.md) §4.1 D1。
2. **触发图质量**:识别目标须**特征丰富、纹理密度高、非重复**;**避免大面积平色天空/墙面、避免重复纹理**(会拉低 VisionKit 特征点数,识别不稳、锁定后易抖)。判断依据见项目 skill `ar-anti-jitter` / `wechat-miniprogram-ar` 的既有结论——**不要拿边缘图/线稿当识别图**(D2 轮廓辅助线只是 UI 引导层,严禁进入识别输入)。
3. **资产落点(ASSET_LAYOUT 铁律)**:源片落 `_assets-src/triggers/<spot>/` + `PROVENANCE.md`(记拍摄日期/时段/机位/EXIF);压缩生产 marker 落 `wechat-gucheng/miniprogram/ar/assets/markers/<spot>-marker.jpg`。参考图/触发图/动画美术图三类目录严禁混放。
4. **登记即凭证**:新增/替换任一触发图或 marker,**同一改动内**更新 [`manifest.json`](manifest.json),`npm run ar:assets:check` 必须绿。
