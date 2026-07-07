# Topology / UV Rubric v01

This rubric applies after asset-art acceptance and before rigging.

The topology/UV gate asks whether the accepted visual source has become an
animation-ready mesh with usable material continuity.

## Required Evidence

- Topology wireframe board.
- Edge-loop closeup board.
- UV layout board.
- Texel-density board.
- Normal/AO/curvature bake check.
- Profile-specific topology/UV boards from `profiles/asset-profiles.json`.

## Hard Rejects

- Automatic retopo is treated as final without deformation-loop review.
- Head/neck/body, face/shoulder/hand, robe/sleeve, or key prop edges lack the
  loop structure required by the profile.
- UV seams cross hero closeup areas without art justification.
- Texture direction breaks at a biologically or culturally important join.
- Bake output hides topology failure rather than preserving sculpt detail.

## Reviewer Output

The review must name the exact loops or UV islands that pass/fail and whether
rigging may start. A pass here does not accept rig, motion, source-pass, or
runtime.
