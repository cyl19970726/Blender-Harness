# Synthetic Accepted Control Fixture

This fixture is a **positive control for `check-gate-status.mjs` only**. It is a
minimal, fully-synthetic candidate whose `gate-status.json` and single
`reviews/fresh-visual-review.json` are hand-written so that:

- every `required_reviews` role has a matching review with `verdict: accept`,
- `status` is `accepted`,
- `downstream_allowed` is `true` (consistent with the accepted status),
- no `forbidden_next_outputs` exist.

It exists so the regression harness can prove the checker's **accepted / exit 0**
path, the mirror image of the golden-negative fixture at
`../gate-d-v01-negative/`.

## This is NOT a visual precedent

This candidate ships **no media** — no frames, no video, no boards, no `.blend`.
The scores in its review are placeholder fives, not the outcome of any real
independent visual review. It backs no real artifact and must never be cited as
evidence that any Gate passed, that any dragon/animation/asset was accepted, or
that any downstream render/runtime work is visually justified.

Per issue #131 and the checker's own README: a checker exit code of `0` means
"review records are present and all accept," **not** a visual endorsement. This
fixture is exactly the case that distinction protects — a green checker on
zero real visual work.
