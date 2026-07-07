# Asset Art Rubric v01

This rubric applies before topology, rig, animation, source-pass, or runtime.

The asset-art gate asks one question: does this asset deserve to exist as a
visible product asset?

## Required Evidence

- Material-preview board with no helpers.
- Clay board.
- Wireframe board.
- Silhouette board.
- Primary closeup board with no helpers.
- Profile-specific closeups from `profiles/asset-profiles.json`.
- Source manifest with license and provenance.
- Artifact manifest consumed by `check-artifacts.mjs`.

## Hard Rejects

- The asset only works from far away.
- Helper collars, sockets, axes, or guide overlays hide the visible problem.
- A hero closeup shows seams, broken scale flow, broken material continuity, or
  placeholder geometry.
- The source is unclear, unlicensed, or marked as final while it is raw/proxy.
- The asset profile's hard rejects fire.

## Profile-Specific Focus

- `long_creature`: head-neck-body continuity, belly/dorsal flow, tail-root, and
  no decorated tube/slab read.
- `humanoid_character`: face identity, body proportion, outfit/material,
  accessory fit, and no generic NPC read.
- `historical_figure`: historical costume accuracy, dignity, age/silhouette,
  robe/sleeve material, and gesture tone.
- `building_prop`: structure joins, hard-edge material, anchor/scale, and
  pass-owner separability.
- `product_prop`: product edge, finish, scale with marker, and closeup texture.

## Reviewer Output

The review must answer:

- Pass or reject?
- Which exact board/frame proves the decision?
- Which downstream steps remain locked?
- What must be rebuilt or resubmitted next?

Numeric scores are optional context only. They cannot override hard rejects.
