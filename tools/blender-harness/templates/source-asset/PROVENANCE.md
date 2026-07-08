# Source Asset Provenance Template

Copy this file to `_assets-src/<asset-id>/PROVENANCE.md` when creating a new
source asset package.

## Asset

```text
asset_id:
asset_profile: long_creature | humanoid_character | historical_figure | building_prop | product_prop
owner:
created_at:
issue:
product_surface:
```

## Directory Contents

| Path | Purpose | Git policy | Notes |
|---|---|---|---|
| `asset-brief.md` | production brief | commit | |
| `identity-capsule.md` | visual identity lock | commit | |
| `00_style_lock/` | small style/reference boards | commit only cleared small files | |
| `01_3d_ready_turnaround/` | neutral front/side/back/top/hero45 sheets | commit only cleared small files | |
| `02_accessory_split/` | component split and ownership boards | commit only cleared small files | |
| `03_material_refs/` | material reference boards | commit only cleared small files | |
| `04_hunyuan_inputs/` | Hunyuan-ready input images/manifests | commit only cleared small files | |
| `manifests/` | source, ownership, archive manifests | commit | |

## Source Of Truth

Record which files are authoritative. Do not list temporary generations as
approved source.

| File | Role | Source / Tool | License / Usage | SHA256 |
|---|---|---|---|---|
| | | | | |

## Heavy Binary Archive

Large binaries must not be committed by default. Store them in `.artifacts`
during production. If they must be preserved, upload to CloudBase/COS or GitHub
Release and record them here.

| File | Local working path | Archive URL | Size | SHA256 | Purpose |
|---|---|---|---:|---|---|
| raw GLB | `.artifacts/hunyuan/<asset-id>/<run-id>/raw/hunyuan_raw.glb` | | | | source |
| source `.blend` | `.artifacts/blender-harness/<candidate-id>/00_inputs/source_assets/*.blend` | | | | production working |

## Derivation Chain

Use arrows to show how source moved through tools.

```text
reference/style lock
  -> 3D-ready source sheets
  -> Hunyuan/manual/market source
  -> Blender cleanup/high sculpt
  -> retopo/UV/material
  -> rig/deformation
  -> animation/source-pass/runtime
```

If any step is inferred rather than proven, write that explicitly. Do not invent
provenance.

## Gate Evidence

| Gate | Candidate dir | Reduced evidence dir | Verdict | Review files |
|---|---|---|---|---|
| asset_art | `.artifacts/blender-harness/<candidate-id>/` | (pending per ADR 0007 open item) | pending | |
| topology_uv | | | pending | |
| rig_deformation | | | pending | |
| animation | | | pending | |
| source_pass | | | pending | |

## Storage Decision

```text
git_light_sources:
local_artifacts:
durable_archive:
runtime_location:
git_lfs_required: no
```

Git LFS must stay `no` unless a separate repo-level decision explicitly enables
large binary versioning for this asset class.

## Open Questions

- 
