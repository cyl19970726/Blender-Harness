# Complex Creature Example: Long Dragon

This example shows how to use Blender Harness for a difficult organic creature. It is not a claim that the current dragon asset is accepted or production-ready.

The long dragon is intentionally the hardest small example in this package: it combines art direction, a long continuous body, dense surface detail, retopo, UV continuity, spline-style rigging, closeup deformation, camera blocking, and same-source pass ownership.

## Why This Example Exists

The previous dragon attempts exposed a root failure mode: the head and body were not a single continuous source asset. Later phases tried to hide that with collars, sockets, mane, bridge meshes, camera angles, or animation. Blender Harness should prevent that failure from reaching retopo, rig, animation, source-pass, or runtime.

The harness value is therefore:

- detect the source-asset failure early,
- reject the candidate at the correct gate,
- route the work back upstream,
- preserve prompt-bound Human / Agent review evidence,
- prevent downstream artifacts from appearing before acceptance.

## Profile

Use:

```json
{
  "asset_profile": "long_creature",
  "current_gate": "asset_art"
}
```

The `long_creature` profile protects:

- head-neck-body continuity,
- belly scale flow,
- dorsal mane/fin flow,
- tail-root continuity,
- S-curve / tight-coil / around-column / near-lens deformation,
- head turn, jaw, whiskers, horns, claws, and tail controls.

## Non-Goals

- Do not use this example to justify shipping an unfinished dragon.
- Do not treat Hunyuan, marketplace scans, auto-retopo, or generated object passes as final by default.
- Do not repair a source seam with collar, socket, helper mesh, fur, mane, or camera framing.
- Do not enter retopo, rig, animation, source-pass, or runtime before the upstream gate accepts.

## Full Harness Route

```text
reference / art direction
  -> single-source creature design
  -> source surface / sculpt
  -> retopo / UV / material
  -> rig / deformation
  -> animation blocking / polish
  -> source-pass
  -> runtime
```

Each phase needs a candidate directory:

```text
candidate-manifest.json
artifact-manifest.json
prompt-manifest.json
source-manifest.json
evidence/
reviews/
gate-status.json
```

Run:

```bash
cd tools/blender-harness
npm run check-artifacts -- <candidate-dir> --json
npm run check-gate-status -- <candidate-dir> --json
```

## Phase Gates

### P1 Reference / Art Direction

Accepted evidence:

- reference mood board,
- morphology notes,
- rigged dragon market/reference analysis,
- motion references,
- license/provenance notes,
- style/color/proportion decision.

Reject when references are generic, unlicensed, not comparable, or do not explain the head-neck-body relationship.

### P2 Single-Source Creature Design

Accepted evidence:

- front / back / side / top / hero45 design sheets,
- head closeup,
- belly/dorsal callout,
- tail-root callout,
- scale-flow callout.

Reject when the concept reads as a good head plus a pipe/tube/slab body.

### P3 Source Surface / Sculpt

Accepted evidence:

- material preview board,
- clay board,
- wireframe board,
- silhouette board,
- no-helper viewport board,
- primary closeup board,
- head-neck closeup board,
- belly-dorsal closeup board,
- tail-root closeup board,
- scale-flow callout board.

Reject when any closeup needs a helper collar, socket, guide, or camera angle to hide source discontinuity.

### P4 Retopo / UV / Material

Accepted evidence:

- topology wireframe board,
- head-neck loop board,
- body ring loop board,
- belly UV continuity board,
- UV layout board,
- texel density board,
- bake check board.

Reject when automatic retopo is treated as final without proving deformation-ready loops and material continuity.

### P5 Rig / Deformation

Accepted evidence:

- neutral pose board,
- extreme pose board,
- closeup deformation board,
- S-curve pose board,
- tight-coil pose board,
- around-column pose board,
- near-lens lunge pose board,
- head turn / jaw board,
- tail whip board,
- claw spread board.

Reject when coil, lunge, head turn, or tail motion collapses in closeup.

### P6 Animation

Accepted evidence:

- camera playblast,
- camera timeline board,
- top timeline board,
- side timeline board,
- asset-only timeline board,
- high-coverage contact sheet,
- orbit path board,
- near-lens lunge contact sheet,
- head-neck motion closeup board.

Reject when the camera hides asset or rig problems.

### P7 Source-Pass / Runtime

Accepted evidence:

- beauty contact sheet,
- pass breakdown board,
- owner collection manifest,
- matte contact sheet,
- source-pass audit,
- runtime boundary audit.

Reject when beauty, pass, and matte ownership are not same-source. Runtime packaging is locked until this accepts.

## Reviewer Roles

Use Human or Agent reviewers. Subagents may execute these roles in the main production thread; this example only defines the contract.

| Phase | Reviewer roles |
|---|---|
| Reference | `art_director`, `provenance_reviewer` |
| Design / source surface | `asset_art_reviewer`, `fresh_visual_reviewer` |
| Retopo / UV | `topology_reviewer`, `uv_material_reviewer` |
| Rig / deformation | `rig_reviewer`, `deformation_reviewer`, `fresh_visual_reviewer` |
| Animation | `animation_reviewer`, `fresh_visual_reviewer` |
| Source-pass | `source_pass_reviewer`, `runtime_boundary_reviewer`, `fresh_visual_reviewer` |

## Canary Failures

The harness should reject these without debate:

- `head_neck_body_seam_visible`
- `decorated_tube_or_slab_body`
- `helper_collar_or_socket_masks_art_failure`
- `scale_or_belly_flow_breaks_at_neck_or_tail`
- `coil_or_lunge_closeup_collapses`
- `camera_hides_asset_failure`
- `source_pass_owner_not_same_source`

`fixtures/asset-art-head-neck-negative` is the first canary for this example. It must remain blocked by `check-artifacts`.
