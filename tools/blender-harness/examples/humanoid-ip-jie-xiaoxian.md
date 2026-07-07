# Humanoid IP Example: Jie Xiaoxian

Status: process example only; not fully verified as a production asset.

This example shows how to use Blender Harness for a stylized humanoid IP character from concept/reference through 3D generation, cleanup, topology, UV/material, rigging, and gesture animation.

It is intentionally different from the long dragon example. Jie Xiaoxian is not a continuous long-body creature problem. The hard problems are identity, face, proportions, clothing, accessories, hands, expression, retargeting, and whether the character still reads as Jieyang Gucheng's IP after deformation and motion.

## Profile

Use:

```json
{
  "asset_profile": "humanoid_character",
  "current_gate": "asset_art"
}
```

The `humanoid_character` profile protects:

- face and silhouette identity,
- body proportions,
- outfit and material read,
- accessories,
- hands and sleeves,
- face expression,
- clothing/accessory deformation,
- retargeted motion personality.

## Non-Goals

- Do not treat one generated GLB as final just because it loads in Blender.
- Do not accept a generic game NPC read.
- Do not hide face, hands, sleeves, or accessories in distant shots.
- Do not let Hunyuan AutoRig or text-to-motion bypass Blender rig/deformation review.
- Do not enter animation or runtime before asset art, topology/UV, and rig/deformation gates accept.

## Full Harness Route

```text
IP art direction
  -> character design sheet
  -> Hunyuan / manual / marketplace source
  -> Blender cleanup / source surface
  -> retopo / UV / material
  -> rig / deformation
  -> gesture animation
  -> runtime GLB / source-pass when needed
```

Each candidate needs:

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

### P1 IP Art Direction

Accepted evidence:

- Jie Xiaoxian reference board,
- target age/personality notes,
- face/silhouette references,
- outfit and accessory reference,
- color/material palette,
- intended motion set such as idle, greeting, guiding, pouring tea, or stamp interaction.

Reject when references are generic mascot references and do not define the specific IP read.

### P2 Character Design Sheet

Accepted evidence:

- front / back / side / top / hero45 sheet,
- face closeup,
- body proportion board,
- outfit callout,
- accessory callout,
- hand and sleeve callout.

Reject when the design reads as a generic child NPC, generic tourist mascot, or a style that cannot be recognized as the intended IP.

### P3 Source Mesh / Asset Art

Accepted source paths:

- Hunyuan image-to-3D or multi-view-to-3D as raw source,
- manual Blender/ZBrush modeling,
- licensed marketplace base only if license and modification rights are clear.

Accepted evidence:

- material preview board,
- clay board,
- wireframe board,
- silhouette board,
- no-helper viewport board,
- face closeup board,
- body proportion board,
- outfit material board,
- accessory closeup board,
- source-manifest with provenance and license clearance.

Reject when the face, silhouette, outfit, or accessories only work from far away.

### P4 Retopo / UV / Material

Accepted evidence:

- topology wireframe board,
- face loop board,
- shoulder / elbow / hand loop board,
- outfit UV board,
- UV layout board,
- texel density board,
- bake check board.

Retopo requirements:

- face loops support expression,
- shoulders/elbows/wrists/hands support gesture,
- sleeve and clothing edges deform without tearing,
- accessories are either bound, constrained, or intentionally rigid with stable pivots.

Reject when auto-retopo destroys face expression zones, hands, sleeve cuffs, or accessory boundaries.

### P5 Rig / Deformation

Hunyuan AutoRig may be useful as a draft or starting point. Final acceptance still belongs in Blender.

Accepted evidence:

- rig hierarchy audit,
- skin weight audit,
- neutral pose board,
- extreme pose board,
- closeup deformation board,
- face expression board,
- hand pose board,
- sleeve/accessory deformation board,
- retarget neutral pose board.

Reject when hands collapse, sleeves clip, accessories float, face expression breaks, or retargeting changes the character's personality.

### P6 Gesture Animation

Accepted evidence:

- camera playblast,
- camera timeline board,
- top/side/asset-only timeline boards where useful,
- gesture timing board,
- facial expression timeline board,
- character personality review board.

Suggested initial motions:

- idle breathing,
- greeting,
- pointing/guiding,
- holding or presenting a cultural object,
- simple tea-pouring only if props and sleeves already pass rig/deformation.

Reject when the motion reads as generic Mixamo-style motion with no IP personality.

### P7 Runtime / Source-Pass

Accepted evidence:

- runtime GLB size and material audit,
- animation clip audit,
- texture compression audit,
- source-pass boards only when rendering precomposited video/pass outputs.

Reject when runtime optimization changes the face, outfit, color, silhouette, or animation timing enough to break the accepted character read.

## Reviewer Roles

Use Human or Agent reviewers. Subagents may execute these roles in the main production thread; this example only defines the contract.

| Phase | Reviewer roles |
|---|---|
| IP art direction / design | `asset_art_reviewer`, `fresh_visual_reviewer`, optional `ip_style_reviewer` |
| Source mesh / asset art | `asset_art_reviewer`, `fresh_visual_reviewer` |
| Retopo / UV | `topology_reviewer`, `uv_material_reviewer` |
| Rig / deformation | `rig_reviewer`, `deformation_reviewer`, `fresh_visual_reviewer` |
| Gesture animation | `animation_reviewer`, `fresh_visual_reviewer`, optional `ip_personality_reviewer` |
| Runtime | `runtime_boundary_reviewer`, `fresh_visual_reviewer` |

## Difference From Long Dragon

| Topic | Jie Xiaoxian humanoid IP | Long dragon complex creature |
|---|---|---|
| Source continuity | Can be multi-part: body, clothing, hair, accessories, eyes, props | Head, neck, body, belly, dorsal flow, and tail must read as one continuous organism |
| Main art risk | Face identity, cute/stylized proportion, outfit, hands, accessories | Head-neck-body seam, decorated tube body, scale/belly/dorsal flow |
| Retopo risk | Face loops, hands, shoulders, sleeves, clothing boundaries | Body rings, head-neck loops, belly UV continuity, long-body twist |
| Rig strategy | Biped armature, face controls, hands, clothing/accessory constraints, retarget checks | Spline IK/B-Bones/curve controls, jaw/whisker/horn/claw/tail controls |
| Animation risk | Generic retarget motion erases IP personality | Camera hides asset/rig failure; coil/lunge/near-lens deformation collapses |
| Hunyuan role | More useful for first humanoid mesh, AutoRig draft, and text-to-motion draft | More useful as source inspiration; final long-body sculpt/retopo/rig needs stronger manual control |

## Canary Failures

The harness should reject these:

- `face_or_silhouette_off_character`
- `generic_game_npc_read`
- `hands_or_face_collapse_in_closeup`
- `accessory_or_clothing_not_bound`
- `retarget_motion_breaks_character_personality`
- `hunyuan_autorig_used_as_final_without_deformation_gate`

`fixtures/asset-contract-humanoid-accepted` is only a synthetic contract fixture. It is not proof that a real Jie Xiaoxian production asset has passed.
