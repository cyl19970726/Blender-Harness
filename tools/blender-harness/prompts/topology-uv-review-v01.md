# Topology / UV Review Prompt v01

Use this prompt for either a human reviewer or an agent reviewer at the `topology_uv` gate.

## Role

You are the topology and UV reviewer. Decide whether the accepted art source has become a deformation-ready mesh with usable UV and material continuity.

## Inputs

- `candidate-manifest.json`
- `artifact-manifest.json`
- profile-specific topology, wireframe, loop, UV, texel density, and bake boards
- `rubrics/topology-uv-rubric-v01.md`
- `prompts/reference-compare-review-v01.md`
- `prompts/failure-case-checklist-v01.md`

## Review Rules

- Do not accept a raw generated mesh as final topology just because it loads in Blender.
- Edge loops must support the expected deformation zones.
- UV islands and texel density must preserve material continuity at important joins.
- For long creatures, head-neck-body loops, belly scale direction, dorsal line, and tail root must be continuous enough for bending and twisting.
- For humanoids, face, shoulder, elbow, wrist, hand, clothing, and accessory loops must support closeup motion.
- Bake checks must show normal, AO, curvature, and material details are not broken by retopo or UV seams.

## Required Output

Write `reviews/<role>-review.json` with:

- `role`
- `prompt_id: "topology-uv-review-v01"`
- `prompt_version: "v01"`
- `rubric_version`
- `verdict`
- `hard_reject_hits`
- `findings`: cite exact wireframe, UV, bake, or closeup boards
- `downstream.full_render`
- `downstream.wechat_runtime`
- `suggested_next_step`

`conditional` does not unlock downstream.
