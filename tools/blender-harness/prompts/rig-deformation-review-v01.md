# Rig / Deformation Review Prompt v01

Use this prompt for either a human reviewer or an agent reviewer at the `rig_deformation` gate.

## Role

You are the rig and deformation reviewer. Decide whether the rig deforms the accepted mesh under the poses required by final animation.

## Inputs

- `candidate-manifest.json`
- `artifact-manifest.json`
- rig hierarchy audit
- skin weight audit
- neutral, extreme, closeup deformation, and profile-specific pose boards
- `rubrics/rig-deformation-rubric-v01.md`
- `prompts/failure-case-checklist-v01.md`

## Review Rules

- Do not accept a rig that only works in neutral pose.
- Closeup deformation has priority over distant silhouette.
- For long creatures, validate S curve, tight coil, around-column pose, near-lens lunge, head turn, jaw, tail whip, and claw spread.
- For humanoids, validate face, hands, clothing, sleeves, accessories, retarget neutral, and expressive poses.
- Reject if deformation hides by camera angle, helper mesh, collar, socket, or omitted closeup.
- Rig controls must be understandable enough for animation blocking, not only script-driven one-off transforms.

## Required Output

Write `reviews/<role>-review.json` with:

- `role`
- `prompt_id: "rig-deformation-review-v01"`
- `prompt_version: "v01"`
- `rubric_version`
- `verdict`
- `hard_reject_hits`
- `findings`: cite exact pose boards and closeups
- `downstream.full_render`
- `downstream.wechat_runtime`
- `suggested_next_step`

`conditional` does not unlock downstream.
