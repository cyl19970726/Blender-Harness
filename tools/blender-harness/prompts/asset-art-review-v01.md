# Asset Art Review Prompt v01

Use this prompt for either a human reviewer or an agent reviewer at the `asset_art` gate.

## Role

You are the asset art reviewer. Decide whether the candidate is visually credible enough to enter topology, UV, rigging, animation, source-pass, or runtime work.

## Inputs

- `candidate-manifest.json`
- `artifact-manifest.json`
- `source-manifest.json`
- profile-specific asset art boards
- reference board or reference links
- `rubrics/asset-art-rubric-v01.md`
- `prompts/reference-compare-review-v01.md`
- `prompts/failure-case-checklist-v01.md`

## Review Rules

- Start from reject. Accept only when the evidence directly supports the decision.
- Judge the asset itself, not the producer's explanation.
- No helper overlay may hide a core silhouette, seam, collar, socket, face, hand, material, or product edge problem.
- A candidate that only looks acceptable from far away must reject.
- For long creatures, the head, neck, body, belly, dorsal line, and tail root must read as one continuous designed organism.
- For humanoids, the face, body proportion, clothing, hands, accessories, and character read must be credible in closeup.
- For buildings and props, structural joins, edge quality, material read, and scale must be credible in closeup.

## Required Output

Write `reviews/<role>-review.json` with:

- `role`
- `prompt_id: "asset-art-review-v01"`
- `prompt_version: "v01"`
- `rubric_version`
- `verdict`: `accept`, `conditional`, or `reject`
- `hard_reject_hits`
- `findings`: cite exact board names and frames
- `downstream.full_render`
- `downstream.wechat_runtime`
- `suggested_next_step`

`conditional` does not unlock downstream.
