---
name: jygc-dragon-rig-pipeline
description: 揭阳古城 AR 磁贴/景点里的东方长身龙资产产线。当任务涉及龙、长身龙、Loong、龙绕楼、盘龙、扑镜、龙的三视图、Hunyuan 生成完整龙或龙部件、组件拆分、UV/拓扑/纹理、Blender 龙绑骨、Spline IK/B-Bones、curve rig、动画参考、或判断龙资产能否进入 rig/animation/P9 时使用。它要求先做参考和原创设计,再用 Hunyuan 做 source/candidate,最后由 Blender harness 决定能否进入生产。
---

# JYGC Dragon Rig Pipeline

This skill is the project-local production discipline for premium Chinese
long-dragon assets in Jieyang Gucheng AR. It sits between:

- `jygc-magnet-animation`: product contract and P9 visual veto;
- `hunyuan-3d`: Tencent Hunyuan 3D API capabilities;
- `blender-harness`: multiview boards, reviewers, and gate-status checks.

## Non-Negotiables

- This is a premium AR cultural-souvenir asset, not a Hunyuan prompt contest.
- Technical success cannot approve ugly frames.
- Do not default to a generic gold dragon. Preferred project palette is jade /
  teal / cream / coral / restrained brass.
- A curve is not a dragon. A decorated tube, capsule, rail, or low-poly proxy
  is a hard reject outside explicit planning scope.
- Third-party marketplace assets are reference evidence only unless license,
  provenance, and reuse terms are explicitly cleared.
- Hunyuan raw output is a visual/source candidate, never final by itself.
- Every downstream unlock needs multiview evidence plus independent review.

## Source-Surface Contract

Use this split for every visible dragon asset:

- **Visual source asset**: source sheet / Hunyuan raw mesh / material reference.
  It carries silhouette, enamel material, scales, belly plates, mane, fins,
  claws, whiskers, horns, tail plume, and closeup value.
- **Production control asset**: Blender retopo, sockets, segmentation, rig
  controls, animation paths, source passes, and harness evidence. It carries
  deformation, ownership, reproducibility, and runtime viability.

Never promote a source or proxy just because it looks useful. The next step
after a useful source is source-preserving cleanup / retopo / lookdev, not
animation blocking.

## Reusable Assets From Previous Exploration

Use previous work as evidence, not as automatic final input:

| Asset | Reuse As | Do Not Use As |
|---|---|---|
| Dragon head style board / source sheet | Style bible for full-dragon model sheets: teal scales, cream belly, coral mane, brass horns/lines, enamel material | Final texture/IP copy without review |
| `jxm-long-dragon-head-source-preserving-v04` | Head visual standard and control-proof source | Full-body rig or final animated head |
| `jxm-long-dragon-b0-art-v01` | Palette and art direction | Final render evidence |
| tail / neck raw Hunyuan modules | Tail plume, belly strip, neck mane, dorsal-fin visual source | Topology, rig, final mesh |
| body source-preserving mesh | Body socket / belly / dorsal owner planning | Deformation-ready body |
| limb/claw source | Five-claw semantics and color language | Rig-ready claw mesh |

## Full-Dragon Source Route

Use this route when module stitching is losing proportion, silhouette, or
overall dragon momentum:

```text
original full-dragon concept / multiview source sheet
  -> Hunyuan 3D Pro full-dragon raw source
  -> Blender raw import check
  -> Hunyuan component split candidate
  -> Blender collection/pass-owner check
  -> Hunyuan reduce/topology / UV / texture candidates
  -> Blender source-preserving cleanup / manual retopo
  -> Blender long-body rig: Spline IK / B-Bones / curve controls
  -> rig pose harness
  -> animation blocking
  -> P9 visual gate
```

This route is a source-route experiment. It does not create a one-click final
dragon.

## Hunyuan Generation Policy

Recommended Hunyuan roles:

- full dragon raw source: `Model=3.1`, multiview, high face count, PBR allowed;
- hero modules: head, neck, body, limb/claw, tail, material references;
- component split: candidate owner extraction, not final pass ownership;
- reduce/topology, UV, texture: candidates only, all must return to Blender QA.

Face-count policy:

- source / hero closeup: use high face counts when needed, including
  `120000-800000`, and only test `1500000` when source detail truly needs it;
- rig/animation/runtime: do not use raw high-poly output directly;
- mobile runtime target must be reduced or retopoed and optimized separately.

## Full-Dragon Source Sheet Requirements

Before calling Hunyuan, the source sheet must prove:

- front, side, back, top, and hero45 are visually consistent;
- head style inherits the accepted enamel dragon-head direction;
- long body is long enough to coil/orbit, not a short snake;
- at least four limb groups are visible and planned; for the long-body AR
  direction, six visible limbs / three pairs may be used when it improves
  orbit readability, but it must not read as an insect or centipede;
- belly plates run continuously from neck through tail;
- dorsal fins / mane / tail plume have direction and rhythm;
- palette is jade/teal/cream/coral/brass, not full-gold toy;
- it is not Shenron, not a western dragon, and not a generic stock dragon.

## Gates

### P0 Route Definition

Allowed: route docs, issue comments, source-sheet spec, capability matrix.

Forbidden: Hunyuan spend, model generation, rig, animation.

### P1 Source Sheet

Required boards: front, side, back, top, hero45, material closeup, reusable
asset board.

Hard reject: inconsistent views, no back volume, no limbs/five claws, no belly
continuity, generic gold toy, copied third-party expression.

### P2 Full-Dragon Raw Source

Required evidence: Hunyuan submit/query JSON, raw GLB/FBX, download log,
Blender import report, front/back/side/top/hero45/closeup/wire/material board.

Hard reject: short snake, fused claws, broken tail, severe support rods, back
side unusable, toy material, poor closeup.

### P3 Component Split

Required evidence: parts raw, part manifest, segmentation info, Blender
collection ownership board, source-pass-audit JSON.

Hard reject: key parts fragmented beyond repair, pivot unusable, semantic owner
mapping unclear, mane/fins/tail plume destroyed.

### P4 Topology / UV / Texture Candidate

Required evidence: wire board, UV/texel-density board, material closeup board,
topology report.

Hard reject: no continuous long-body loops, bend zones collapse, UV stretch on
hero closeups, material loses enamel value.

### P5 Source-Preserving Cleanup / Retopo

Required evidence: source vs cleanup board, clay, wire, closeup, underside,
socket views, loose-part audit, model-topology review, global-observer review.

This is the first phase that may unlock rig proof.

### P6 Rig Proof

Recommended rig: Blender Spline IK / B-Bones / curve controls, plus local jaw,
whisker, horn, claw, mane, and tail controls as needed.

Required poses: neutral, S curve, C curve, tight coil, wrap tower, over/under
pass, lunge, extreme bend, head-tail aim, jaw roar, claw pose.

Hard reject: twist, candy-wrapper body, collapsed belly plates, drifting claws,
unbaked plugin output.

### P7 Animation Blocking

Required views: main camera, top path, side path, dragon-only, head/nose/tail
paths, high-coverage contact sheet.

Hard reject: path translation instead of dragon motion, body reads as tube,
foreground lunge reads as proxy blob, loop seam breaks.

## Required Review Pattern

Before each downstream unlock, run at least:

- model/topology reviewer;
- global art observer;
- rig/motion reviewer for P6/P7;
- source/pass integrity reviewer for P3/P8.

The global observer cannot accept a phase alone, but can block or route it
upstream when the work drifts away from the product.

## Directory Contract

The full-dragon source route is paused; its research directory was deleted with docs architecture v2 (recover via git history @03940cf8). Historical layout for reference:

```text
docs/research/ar-magnet/jinxianmen/full-dragon-route-v01/   (deleted @03940cf8)
  README.md
  p0-p1-route-brief.md
  reusable-asset-register.md
  hunyuan-api-capability-matrix.md
  source-sheet-spec-v01.md
  manifest.json
```

Heavy assets stay outside git:

```text
.artifacts/hunyuan/<asset-id>/<run-id>/
.artifacts/blender-harness/<candidate-id>/
.artifacts/reference-captures/<reference-id>/
```
