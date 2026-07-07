# Source-Pass Review Prompt v01

Use this prompt for either a human reviewer or an agent reviewer at the `source_pass` gate.

## Role

You are the source-pass reviewer. Decide whether beauty, pass ownership, matte, and runtime boundary evidence are same-source and ready for packaging.

## Inputs

- `candidate-manifest.json`
- `artifact-manifest.json`
- beauty contact sheet
- pass breakdown board
- owner collection manifest
- matte contact sheet
- source-pass audit
- runtime boundary audit
- `rubrics/source-pass-rubric-v01.md`
- `prompts/failure-case-checklist-v01.md`

## Review Rules

- Passes must come from the same accepted source scene or source render graph.
- Automatic masks, generated-video object passes, and background removal may guide work, but cannot occupy final source-pass slots.
- Each matte owner must be named and bounded by frame range.
- Reject full-frame alpha, slab windows, unexplained frame-edge mattes, owner leaks, and post-hoc masks that do not match accepted animation.
- Runtime packaging cannot start until this gate accepts.

## Required Output

Write `reviews/<role>-review.json` with:

- `role`
- `prompt_id: "source-pass-review-v01"`
- `prompt_version: "v01"`
- `rubric_version`
- `verdict`
- `hard_reject_hits`
- `findings`: cite exact beauty/pass/matte/audit boards
- `downstream.full_render`
- `downstream.wechat_runtime`
- `suggested_next_step`

`conditional` does not unlock downstream.
