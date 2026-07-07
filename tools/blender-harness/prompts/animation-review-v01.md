# Animation Review Prompt v01

Use this prompt for either a human reviewer or an agent reviewer at the `animation` gate.

## Role

You are the animation reviewer. Decide whether the motion, camera, staging, and profile-specific action read correctly from multiple views.

## Inputs

- `candidate-manifest.json`
- `artifact-manifest.json`
- camera playblast
- camera, top, side, asset-only, and high-coverage boards
- profile-specific motion closeups
- `rubrics/animation-rubric-v01.md`
- `prompts/reference-compare-review-v01.md`
- `prompts/failure-case-checklist-v01.md`

## Review Rules

- Motion must be judged from video or dense frame strips, not a single still.
- Camera motion cannot compensate for broken asset art, topology, or rig deformation.
- For long creatures, check orbit path, scale of body, head-neck motion, near-lens lunge, self-overlap, and readable coil timing.
- For humanoids, check gesture timing, face/hand readability, personality, clothing motion, and cultural tone.
- High-coverage frames are risk frames. Inspect them first.
- Reject if the action reads as a path-following object, a smooth tube, a generic NPC loop, or a camera trick.

## Required Output

Write `reviews/<role>-review.json` with:

- `role`
- `prompt_id: "animation-review-v01"`
- `prompt_version: "v01"`
- `rubric_version`
- `verdict`
- `hard_reject_hits`
- `findings`: cite exact frame ranges, boards, or playblast timecodes
- `downstream.full_render`
- `downstream.wechat_runtime`
- `suggested_next_step`

`conditional` does not unlock downstream.
